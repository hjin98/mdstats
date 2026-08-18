"""Packed positive-value periodic scalar fields for LD8 contracts.

LD8-S0 defines the immutable packed scientific-field record and its
backend-neutral accessors.  LD8-S1 uses this record only as a certified storage
contract and adapter target; production target-owned convolution begins in
LD8-S2.

Inactive and exact-zero logical nodes are implicit zeros.  Positive values are
stored in ascending local C-order within each C-order-sorted active block.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .density_block_routing import (
    bitset_popcount,
    bitset_popcounts,
    block_grid_shape,
    local_node_count,
    local_word_count,
    pack_local_indices,
    unpack_local_bitset,
)
from .density_contracts import (
    DISCRETE_PERIODIZED_OPERATOR,
    LOCAL_SPARSE_BACKEND,
    DensitySourceProvenance,
    DensityStorageSummary,
    FrozenJSONMapping,
    freeze_json_mapping,
)
from .density_sparse_reference import SparseCanonicalDensityReference3D, SparseHDRDetails
from .density_hdr import (
    DensityContourSupport,
    DensityHDRBatch,
    prepare_contour_support_many,
    select_hdr_details_many,
)
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
UInt64Array = NDArray[np.uint64]

PERIODIC_PACKED_BLOCK_FIELD_SCHEMA = "mdstats.periodic-packed-block-scalar-field.v1"
DEFAULT_MAX_PACKED_FIELD_NODES = 20_000_000
DEFAULT_MAX_PACKED_FIELD_BLOCKS = 2_000_000
DEFAULT_MAX_PACKED_FIELD_BYTES = 2_000_000_000


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


def _validated_cell(value: Any) -> FloatArray:
    cell = _readonly_array(value, np.float64, ndim=2, name="display_cell")
    if cell.shape != (3, 3):
        raise GraphAdapterError("display_cell must have shape (3, 3).")
    determinant = float(np.linalg.det(cell))
    scale = max(1.0, float(np.linalg.norm(cell, ord=np.inf)) ** 3)
    if abs(determinant) <= 64.0 * np.finfo(np.float64).eps * scale:
        raise GraphAdapterError("display_cell must be nonsingular.")
    return cell


def _flat_block_indices(
    block_indices: NDArray[np.integer], block_grid: tuple[int, int, int]
) -> IntArray:
    result = np.ravel_multi_index(
        (block_indices[:, 0], block_indices[:, 1], block_indices[:, 2]),
        block_grid,
        order="C",
    ).astype(np.int64, copy=False)
    result = np.array(result, dtype=np.int64, copy=True, order="C")
    result.setflags(write=False)
    return result


@dataclass(frozen=True, slots=True)
class PeriodicPackedBlockScalarField3D:
    """Immutable packed positive-value scientific scalar field."""

    field_key: str
    label: str
    physical_units: str
    logical_grid_shape: tuple[int, int, int]
    storage_block_shape: tuple[int, int, int]
    active_block_indices: NDArray[np.int32]
    occupancy_bitsets: UInt64Array
    block_value_offsets: IntArray
    packed_values: FloatArray
    block_min_values: FloatArray
    block_max_values: FloatArray
    display_cell: FloatArray
    total_measure: float
    gaussian_bandwidth: float
    broadening_metric: str
    source_provenance: DensitySourceProvenance
    selected_atom_indices: tuple[int, ...] = ()
    sample_positions: FloatArray | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = PERIODIC_PACKED_BLOCK_FIELD_SCHEMA
    smoothing_operator: str = DISCRETE_PERIODIZED_OPERATOR
    storage_backend: str = LOCAL_SPARSE_BACKEND

    def __post_init__(self) -> None:
        if self.schema_version != PERIODIC_PACKED_BLOCK_FIELD_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported packed-field schema {self.schema_version!r}."
            )
        if self.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR:
            raise GraphAdapterError("Packed fields require discrete_periodized_v1.")
        if self.storage_backend != LOCAL_SPARSE_BACKEND:
            raise GraphAdapterError("Packed fields require local_sparse storage.")
        for name in ("field_key", "label", "physical_units", "broadening_metric"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise GraphAdapterError(f"{name} must be a nonempty string.")
        logical = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        block = _shape3(self.storage_block_shape, name="storage_block_shape")
        grid = block_grid_shape(logical, block)
        indices = _readonly_array(
            self.active_block_indices,
            np.int32,
            ndim=2,
            name="active_block_indices",
        )
        if indices.shape[1:] != (3,) or indices.shape[0] == 0:
            raise GraphAdapterError("active_block_indices must have shape (n, 3), n > 0.")
        if np.any(indices < 0) or np.any(indices >= np.asarray(grid, dtype=np.int32)[None, :]):
            raise GraphAdapterError("active_block_indices lie outside the block grid.")
        flat_blocks = _flat_block_indices(indices, grid)
        if flat_blocks.size > 1 and np.any(flat_blocks[1:] <= flat_blocks[:-1]):
            raise GraphAdapterError("active blocks must be unique and C-order sorted.")
        bitsets = _readonly_array(
            self.occupancy_bitsets,
            np.uint64,
            ndim=2,
            name="occupancy_bitsets",
        )
        words = local_word_count(block)
        if bitsets.shape != (indices.shape[0], words):
            raise GraphAdapterError("occupancy_bitsets do not align with active blocks.")
        counts = bitset_popcounts(bitsets)
        if np.any(counts <= 0):
            raise GraphAdapterError("Every active block must contain positive values.")
        offsets = _readonly_array(
            self.block_value_offsets,
            np.int64,
            ndim=1,
            name="block_value_offsets",
        )
        if offsets.shape != (indices.shape[0] + 1,) or int(offsets[0]) != 0:
            raise GraphAdapterError("block_value_offsets have the wrong shape or origin.")
        if np.any(offsets[1:] < offsets[:-1]) or not np.array_equal(np.diff(offsets), counts):
            raise GraphAdapterError("block_value_offsets disagree with occupancy bit counts.")
        values = _readonly_array(
            self.packed_values, np.float64, ndim=1, name="packed_values"
        )
        if int(offsets[-1]) != values.size or np.any(values <= 0.0):
            raise GraphAdapterError("packed_values must be positive and spanned by offsets.")
        minima = _readonly_array(
            self.block_min_values,
            np.float64,
            ndim=1,
            name="block_min_values",
        )
        maxima = _readonly_array(
            self.block_max_values,
            np.float64,
            ndim=1,
            name="block_max_values",
        )
        if minima.shape != (indices.shape[0],) or maxima.shape != minima.shape:
            raise GraphAdapterError("block extrema must align with active blocks.")
        if np.any(minima < 0.0) or np.any(maxima <= 0.0) or np.any(minima > maxima):
            raise GraphAdapterError("block extrema are invalid.")
        for row in range(indices.shape[0]):
            start, stop = int(offsets[row]), int(offsets[row + 1])
            local_values = values[start:stop]
            expected_max = float(np.max(local_values))
            valid_extent = tuple(
                min(block[axis], logical[axis] - int(indices[row, axis]) * block[axis])
                for axis in range(3)
            )
            valid_count = int(np.prod(valid_extent, dtype=object))
            expected_min = (
                float(np.min(local_values))
                if counts[row] == valid_count
                else 0.0
            )
            if maxima[row] != expected_max or minima[row] != expected_min:
                raise GraphAdapterError("block extrema do not match packed block values.")
            local_flat = unpack_local_bitset(bitsets[row], block)
            local_coords = np.column_stack(
                np.unravel_index(local_flat, block, order="C")
            ).astype(np.int64, copy=False)
            global_coords = indices[row].astype(np.int64)[None, :] * np.asarray(block)[None, :] + local_coords
            if np.any(global_coords >= np.asarray(logical)[None, :]):
                raise GraphAdapterError("Packed field occupies an invalid terminal slot.")
        cell = _validated_cell(self.display_cell)
        total = float(self.total_measure)
        sigma = float(self.gaussian_bandwidth)
        if not np.isfinite(total) or total <= 0.0:
            raise GraphAdapterError("total_measure must be finite and positive.")
        if not np.isfinite(sigma) or sigma < 0.0:
            raise GraphAdapterError("gaussian_bandwidth must be finite and nonnegative.")
        if not isinstance(self.source_provenance, DensitySourceProvenance):
            raise TypeError("source_provenance must be DensitySourceProvenance.")
        atoms = tuple(int(value) for value in self.selected_atom_indices)
        if atoms != tuple(sorted(set(atoms))) or any(value < 0 for value in atoms):
            raise GraphAdapterError("selected_atom_indices must be sorted, unique, and nonnegative.")
        if self.source_provenance.atom_indices and atoms and tuple(self.source_provenance.atom_indices) != atoms:
            raise GraphAdapterError("source_provenance.atom_indices must match selected_atom_indices.")
        samples = None
        if self.sample_positions is not None:
            samples = _readonly_array(self.sample_positions, np.float64, ndim=2, name="sample_positions")
            if samples.shape[1:] != (3,):
                raise GraphAdapterError("sample_positions must have shape (n, 3).")
        object.__setattr__(self, "logical_grid_shape", logical)
        object.__setattr__(self, "storage_block_shape", block)
        object.__setattr__(self, "active_block_indices", indices)
        object.__setattr__(self, "occupancy_bitsets", bitsets)
        object.__setattr__(self, "block_value_offsets", offsets)
        object.__setattr__(self, "packed_values", values)
        object.__setattr__(self, "block_min_values", minima)
        object.__setattr__(self, "block_max_values", maxima)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "total_measure", total)
        object.__setattr__(self, "gaussian_bandwidth", sigma)
        object.__setattr__(self, "selected_atom_indices", atoms)
        object.__setattr__(self, "sample_positions", samples)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))
        if abs(self.integral - total) > 5.0e-13 * max(1.0, total):
            raise GraphAdapterError("Packed field is not normalized to total_measure.")

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.logical_grid_shape

    @property
    def block_grid_shape(self) -> tuple[int, int, int]:
        return block_grid_shape(self.logical_grid_shape, self.storage_block_shape)

    @property
    def voxel_volume(self) -> float:
        return abs(float(np.linalg.det(self.display_cell))) / float(
            np.prod(self.logical_grid_shape, dtype=object)
        )

    @property
    def integral(self) -> float:
        return float(np.sum(self.packed_values, dtype=np.float64)) * self.voxel_volume

    @property
    def active_block_count(self) -> int:
        return int(self.active_block_indices.shape[0])

    @property
    def nonzero_node_count(self) -> int:
        return int(self.packed_values.size)

    @property
    def retained_array_bytes(self) -> int:
        return int(
            self.active_block_indices.nbytes
            + self.occupancy_bitsets.nbytes
            + self.block_value_offsets.nbytes
            + self.packed_values.nbytes
            + self.block_min_values.nbytes
            + self.block_max_values.nbytes
            + (0 if self.sample_positions is None else self.sample_positions.nbytes)
        )

    @property
    def content_identity(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.schema_version.encode("ascii"))
        digest.update(self.field_key.encode("utf-8"))
        digest.update(np.asarray(self.logical_grid_shape, dtype=np.int64).tobytes())
        digest.update(np.asarray(self.storage_block_shape, dtype=np.int64).tobytes())
        digest.update(self.active_block_indices.tobytes(order="C"))
        digest.update(self.occupancy_bitsets.tobytes(order="C"))
        digest.update(self.block_value_offsets.tobytes(order="C"))
        digest.update(self.packed_values.tobytes(order="C"))
        return digest.hexdigest()

    def hdr_details_many(
        self,
        fractions: tuple[float, ...] | list[float],
        *,
        chunk_size: int | None = None,
        max_workspace_bytes: int | None = None,
    ) -> DensityHDRBatch:
        """Resolve several exact HDR thresholds with one bounded value ordering."""

        return select_hdr_details_many(
            self,
            fractions,
            chunk_size=chunk_size,
            max_workspace_bytes=max_workspace_bytes,
        )

    def hdr_details(self, fraction: float) -> SparseHDRDetails:
        return self.hdr_details_many((float(fraction),)).details[0]

    def contour_support_many(
        self,
        fractions: tuple[float, ...] | list[float],
        *,
        compute_components: bool = False,
        chunk_size: int | None = None,
        max_workspace_bytes: int | None = None,
    ) -> tuple[DensityContourSupport, ...]:
        batch = self.hdr_details_many(
            fractions,
            chunk_size=chunk_size,
            max_workspace_bytes=max_workspace_bytes,
        )
        return prepare_contour_support_many(
            self, batch, compute_components=compute_components
        )

    def threshold_for_mass_fraction(self, q: float) -> float:
        return self.hdr_details(q).threshold

    def storage_summary(self) -> DensityStorageSummary:
        return DensityStorageSummary(
            storage_backend=LOCAL_SPARSE_BACKEND,
            logical_grid_shape=self.logical_grid_shape,
            logical_node_count=int(np.prod(self.logical_grid_shape, dtype=object)),
            nonzero_node_count=self.nonzero_node_count,
            stored_value_count=self.nonzero_node_count,
            stored_block_count=self.active_block_count,
            estimated_bytes=self.retained_array_bytes,
            realized_bytes=self.retained_array_bytes,
            metadata={
                "representation": "packed_positive_block_sparse",
                "block_shape": list(self.storage_block_shape),
                "block_grid_shape": list(self.block_grid_shape),
                "bit_order": "c_order_local_index_little_endian_uint64",
                "value_dtype": "float64",
                "block_index_dtype": "int32",
            },
        )

    def to_dense_values(self, *, max_nodes: int) -> FloatArray:
        """Materialize the logical field under caller and runtime node limits."""

        _budget, _model, derived = resolve_density_resource_limits()
        limit = min(
            derived["max_density_voxels"],
            _positive_int(max_nodes, name="max_nodes"),
        )
        logical_count = int(np.prod(self.logical_grid_shape, dtype=object))
        if logical_count > limit:
            raise GraphComplexityError(
                f"Dense materialization needs {logical_count} nodes, exceeding max_nodes={limit}."
            )
        dense = np.zeros(self.logical_grid_shape, dtype=np.float64)
        block = self.storage_block_shape
        for row, block_index in enumerate(self.active_block_indices):
            local_flat = unpack_local_bitset(self.occupancy_bitsets[row], block)
            local_coords = np.column_stack(np.unravel_index(local_flat, block, order="C"))
            global_coords = block_index.astype(np.int64)[None, :] * np.asarray(block)[None, :] + local_coords
            start, stop = int(self.block_value_offsets[row]), int(self.block_value_offsets[row + 1])
            dense[global_coords[:, 0], global_coords[:, 1], global_coords[:, 2]] = self.packed_values[start:stop]
        dense.setflags(write=False)
        return dense

    def iter_stored_nodes(
        self, *, batch_size: int | None = None
    ) -> Iterator[tuple[IntArray, FloatArray]]:
        coordinates_parts: list[IntArray] = []
        values_parts: list[FloatArray] = []
        block = self.storage_block_shape
        for row, block_index in enumerate(self.active_block_indices):
            local_flat = unpack_local_bitset(self.occupancy_bitsets[row], block)
            local_coords = np.column_stack(
                np.unravel_index(local_flat, block, order="C")
            ).astype(np.int64, copy=False)
            global_coords = block_index.astype(np.int64)[None, :] * np.asarray(block)[None, :] + local_coords
            start, stop = int(self.block_value_offsets[row]), int(self.block_value_offsets[row + 1])
            coordinates_parts.append(global_coords)
            values_parts.append(self.packed_values[start:stop])
        coordinates = np.concatenate(coordinates_parts)
        values = np.concatenate(values_parts)
        flat = np.ravel_multi_index(
            (coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]),
            self.logical_grid_shape,
            order="C",
        )
        order = np.argsort(flat, kind="stable")
        coordinates = coordinates[order]
        values = values[order]
        size = int(values.size) if batch_size is None else _positive_int(batch_size, name="batch_size")
        for start in range(0, int(values.size), size):
            stop = min(int(values.size), start + size)
            coordinate_batch = np.array(coordinates[start:stop], dtype=np.int64, copy=True)
            value_batch = np.array(values[start:stop], dtype=np.float64, copy=True)
            coordinate_batch.setflags(write=False)
            value_batch.setflags(write=False)
            yield coordinate_batch, value_batch

    def gather_node_values(self, logical_indices: IntArray) -> FloatArray:
        """Gather arbitrary periodic nodes with one bitset decode per touched block.

        The original LD8 implementation iterated over every query node and decoded
        the owning block's occupancy bitset for every individual lookup.  Tiled
        contour extraction requests dense 33^3 bricks, so that access pattern
        repeated the same block decode tens of thousands of times per tile.  The
        block-grouped implementation below preserves the exact packed-field
        semantics while reducing Python work from O(n_query) block decodes to
        O(n_touched_blocks) decodes.
        """

        query = np.asarray(logical_indices, dtype=np.int64)
        if query.ndim != 2 or query.shape[1:] != (3,):
            raise GraphAdapterError("logical_indices must have shape (n, 3).")
        if query.shape[0] == 0:
            empty = np.empty((0,), dtype=np.float64)
            empty.setflags(write=False)
            return empty

        logical_shape = np.asarray(self.logical_grid_shape, dtype=np.int64)
        block_shape = np.asarray(self.storage_block_shape, dtype=np.int64)
        canonical = np.mod(query, logical_shape[None, :])
        block_coords = np.floor_divide(canonical, block_shape[None, :])
        local_coords = canonical - block_coords * block_shape[None, :]
        query_block_flat = np.ravel_multi_index(
            (block_coords[:, 0], block_coords[:, 1], block_coords[:, 2]),
            self.block_grid_shape,
            order="C",
        ).astype(np.int64, copy=False)
        active_flat = _flat_block_indices(
            self.active_block_indices, self.block_grid_shape
        )
        positions = np.searchsorted(active_flat, query_block_flat)
        result = np.zeros(query.shape[0], dtype=np.float64)
        valid = positions < active_flat.size
        query_rows = np.flatnonzero(valid)
        if query_rows.size == 0:
            result.setflags(write=False)
            return result
        matched = (
            active_flat[positions[query_rows]] == query_block_flat[query_rows]
        )
        query_rows = query_rows[matched]
        if query_rows.size == 0:
            result.setflags(write=False)
            return result

        local_flat = np.ravel_multi_index(
            (local_coords[:, 0], local_coords[:, 1], local_coords[:, 2]),
            self.storage_block_shape,
            order="C",
        ).astype(np.int64, copy=False)
        matched_positions = positions[query_rows]
        order = np.argsort(matched_positions, kind="stable")
        ordered_rows = query_rows[order]
        ordered_positions = matched_positions[order]
        starts = np.concatenate(
            (
                np.asarray([0], dtype=np.int64),
                np.flatnonzero(
                    ordered_positions[1:] != ordered_positions[:-1]
                ).astype(np.int64)
                + 1,
            )
        )
        stops = np.concatenate(
            (starts[1:], np.asarray([ordered_rows.size], dtype=np.int64))
        )
        for start_row, stop_row in zip(starts, stops, strict=True):
            block_position = int(ordered_positions[int(start_row)])
            rows = ordered_rows[int(start_row) : int(stop_row)]
            occupied = unpack_local_bitset(
                self.occupancy_bitsets[block_position], self.storage_block_shape
            )
            if occupied.size == 0:
                continue
            requested = local_flat[rows]
            local_positions = np.searchsorted(occupied, requested)
            inside = local_positions < occupied.size
            if not np.any(inside):
                continue
            candidate_rows = rows[inside]
            candidate_positions = local_positions[inside]
            exact = occupied[candidate_positions] == local_flat[candidate_rows]
            if not np.any(exact):
                continue
            accepted_rows = candidate_rows[exact]
            accepted_positions = candidate_positions[exact]
            value_start = int(self.block_value_offsets[block_position])
            result[accepted_rows] = self.packed_values[
                value_start + accepted_positions
            ]
        result.setflags(write=False)
        return result

    def to_json_dict(self, *, include_arrays: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "label": self.label,
            "physical_units": self.physical_units,
            "logical_grid_shape": list(self.logical_grid_shape),
            "storage_block_shape": list(self.storage_block_shape),
            "total_measure": self.total_measure,
            "gaussian_bandwidth": self.gaussian_bandwidth,
            "broadening_metric": self.broadening_metric,
            "smoothing_operator": self.smoothing_operator,
            "storage_backend": self.storage_backend,
            "active_block_count": self.active_block_count,
            "nonzero_node_count": self.nonzero_node_count,
            "retained_array_bytes": self.retained_array_bytes,
            "content_identity": self.content_identity,
            "display_cell": self.display_cell.tolist(),
            "source_provenance": self.source_provenance.to_json_dict(),
            "selected_atom_indices": list(self.selected_atom_indices),
            "sample_positions": None if self.sample_positions is None else self.sample_positions.tolist(),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_arrays:
            result.update(
                {
                    "active_block_indices": self.active_block_indices.tolist(),
                    "occupancy_bitsets": [
                        [int(value) for value in row] for row in self.occupancy_bitsets
                    ],
                    "block_value_offsets": self.block_value_offsets.tolist(),
                    "packed_values": self.packed_values.tolist(),
                    "block_min_values": self.block_min_values.tolist(),
                    "block_max_values": self.block_max_values.tolist(),
                }
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "PeriodicPackedBlockScalarField3D":
        return cls(
            schema_version=str(value["schema_version"]),
            field_key=str(value["field_key"]),
            label=str(value["label"]),
            physical_units=str(value["physical_units"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            storage_block_shape=tuple(value["storage_block_shape"]),
            active_block_indices=np.asarray(value["active_block_indices"], dtype=np.int32),
            occupancy_bitsets=np.asarray(value["occupancy_bitsets"], dtype=np.uint64),
            block_value_offsets=np.asarray(value["block_value_offsets"], dtype=np.int64),
            packed_values=np.asarray(value["packed_values"], dtype=np.float64),
            block_min_values=np.asarray(value["block_min_values"], dtype=np.float64),
            block_max_values=np.asarray(value["block_max_values"], dtype=np.float64),
            display_cell=np.asarray(value["display_cell"], dtype=np.float64),
            total_measure=float(value["total_measure"]),
            gaussian_bandwidth=float(value["gaussian_bandwidth"]),
            broadening_metric=str(value["broadening_metric"]),
            source_provenance=DensitySourceProvenance.from_json_dict(
                value["source_provenance"]
            ),
            selected_atom_indices=tuple(value.get("selected_atom_indices", ())),
            sample_positions=(
                None
                if value.get("sample_positions") is None
                else np.asarray(value["sample_positions"], dtype=np.float64)
            ),
            metadata=value.get("metadata", {}),
            smoothing_operator=str(value.get("smoothing_operator", DISCRETE_PERIODIZED_OPERATOR)),
            storage_backend=str(value.get("storage_backend", LOCAL_SPARSE_BACKEND)),
        )


def pack_sparse_reference_field(
    field: SparseCanonicalDensityReference3D,
    *,
    storage_block_shape: tuple[int, int, int] = (16, 16, 16),
    max_nodes: int | None = None,
    max_blocks: int | None = None,
    max_retained_bytes: int | None = None,
) -> PeriodicPackedBlockScalarField3D:
    """Pack an LD1-A/LD7 reference field without changing scientific values."""

    if not isinstance(field, SparseCanonicalDensityReference3D):
        raise TypeError("field must be SparseCanonicalDensityReference3D.")
    block = _shape3(storage_block_shape, name="storage_block_shape")
    budget, _model, derived = resolve_density_resource_limits()
    node_default = derived["max_density_nonzero_nodes"]
    node_limit = (
        node_default
        if max_nodes is None
        else min(node_default, _positive_int(max_nodes, name="max_nodes"))
    )
    block_default = derived["max_density_blocks"]
    block_limit = (
        block_default
        if max_blocks is None
        else min(block_default, _positive_int(max_blocks, name="max_blocks"))
    )
    byte_limit = (
        budget.max_memory_bytes
        if max_retained_bytes is None
        else min(_positive_int(max_retained_bytes, name="max_retained_bytes"), budget.max_memory_bytes)
    )
    if field.active_flat_indices.size > node_limit:
        raise GraphComplexityError("Packed field node limit exceeded.")
    logical = field.logical_grid_shape
    grid = block_grid_shape(logical, block)
    coords = np.column_stack(
        np.unravel_index(field.active_flat_indices, logical, order="C")
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
    values = field.active_values[order]
    starts = np.concatenate(
        (
            np.asarray([0], dtype=np.int64),
            np.flatnonzero(block_flat[1:] != block_flat[:-1]).astype(np.int64) + 1,
        )
    )
    unique_blocks = block_flat[starts]
    if unique_blocks.size > block_limit:
        raise GraphComplexityError("Packed field block limit exceeded.")
    indices = np.column_stack(
        np.unravel_index(unique_blocks, grid, order="C")
    ).astype(np.int32, copy=False)
    counts = np.diff(np.concatenate((starts, np.asarray([block_flat.size], dtype=np.int64))))
    offsets = np.concatenate((np.asarray([0], dtype=np.int64), np.cumsum(counts, dtype=np.int64)))
    bitsets = np.vstack(
        [
            pack_local_indices(local_flat[start : start + count], block)
            for start, count in zip(starts, counts, strict=True)
        ]
    ).astype(np.uint64, copy=False)
    maxima = np.asarray(
        [float(np.max(values[start : start + count])) for start, count in zip(starts, counts, strict=True)],
        dtype=np.float64,
    )
    minima: list[float] = []
    for row, (start, count) in enumerate(zip(starts, counts, strict=True)):
        extent = tuple(
            min(block[axis], logical[axis] - int(indices[row, axis]) * block[axis])
            for axis in range(3)
        )
        valid_count = int(np.prod(extent, dtype=object))
        minima.append(float(np.min(values[start : start + count])) if count == valid_count else 0.0)
    minima_array = np.asarray(minima, dtype=np.float64)
    retained = int(
        indices.nbytes
        + bitsets.nbytes
        + offsets.nbytes
        + values.nbytes
        + minima_array.nbytes
        + maxima.nbytes
    )
    if retained > byte_limit:
        raise GraphComplexityError("Packed field retained-byte limit exceeded.")
    return PeriodicPackedBlockScalarField3D(
        field_key=field.field_key,
        label=field.label,
        physical_units=field.physical_units,
        logical_grid_shape=logical,
        storage_block_shape=block,
        active_block_indices=indices,
        occupancy_bitsets=bitsets,
        block_value_offsets=offsets,
        packed_values=values,
        block_min_values=minima_array,
        block_max_values=maxima,
        display_cell=field.display_cell,
        total_measure=field.total_measure,
        gaussian_bandwidth=field.gaussian_bandwidth,
        broadening_metric=field.broadening_metric,
        source_provenance=field.source_provenance,
        metadata={
            **field.metadata.to_json_dict(),
            "packing": "ld8_s0_positive_block_field_adapter_v1",
            "source_schema": field.schema_version,
            "fixed_block_value_bytes": int(unique_blocks.size) * local_node_count(block) * 8,
            "packed_array_bytes": retained,
        },
    )
