"""Production block-sparse periodic scalar density fields.

Architecture gate LD1-B packs the deterministic flat-node LD1-A oracle into
fixed periodic blocks.  The block organization is inspired by the patch-based
local refinement architecture of Berger and Colella (1989); periodic ownership,
partial-block masks, canonical serialization, and resource policies are
project-specific mdstats definitions.

This module changes storage only.  Scientific values are produced by the LD1-A
CIC plus ``discrete_periodized_v1`` reference implementation before packing.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .density_contracts import (
    DISCRETE_PERIODIZED_OPERATOR,
    LOCAL_SPARSE_BACKEND,
    DensitySourceProvenance,
    DensityStorageSummary,
    FrozenJSONMapping,
    freeze_json_mapping,
)
from .density_kernel import PeriodicGaussianStencilSupport
from .density_sparse_reference import (
    DEFAULT_MAX_DENSE_DEBUG_NODES,
    SparseCICNodeMasses3D,
    SparseCanonicalDensityReference3D,
    SparseHDRDetails,
)
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

PERIODIC_BLOCK_FIELD_SCHEMA = "mdstats.periodic-block-scalar-field.v1"
BLOCK_PACKING_PLAN_SCHEMA = "mdstats.block-packing-plan.v1"

DEFAULT_MAX_BLOCKS = 1_000_000
DEFAULT_MAX_STORED_BLOCK_VALUES = 4_000_000
DEFAULT_MAX_NONZERO_NODES = 4_000_000
DEFAULT_MAX_PACKING_WORKSPACE_BYTES = 256_000_000


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _shape3(value: Any, *, name: str, minimum: int = 1) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphAdapterError(f"{name} must contain three entries.")
    result = tuple(_positive_int(item, name=f"{name} entry", minimum=minimum) for item in value)
    return result  # type: ignore[return-value]


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


def _block_lattice_shape(
    logical_shape: tuple[int, int, int], block_shape: tuple[int, int, int]
) -> tuple[int, int, int]:
    return tuple(
        (logical_shape[axis] + block_shape[axis] - 1) // block_shape[axis]
        for axis in range(3)
    )  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class BlockPackingPlan:
    """Exact bounded index plan prepared before block-value allocation."""

    logical_grid_shape: tuple[int, int, int]
    block_shape: tuple[int, int, int]
    block_lattice_shape: tuple[int, int, int]
    active_block_indices: IntArray
    active_block_flat_indices: IntArray
    nonzero_node_count: int
    allocated_value_count: int
    valid_value_count: int
    partial_block_count: int
    planning_bytes: int
    schema_version: str = BLOCK_PACKING_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BLOCK_PACKING_PLAN_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported block-packing-plan schema {self.schema_version!r}."
            )
        logical = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        block = _shape3(self.block_shape, name="block_shape")
        lattice = _shape3(self.block_lattice_shape, name="block_lattice_shape")
        expected_lattice = _block_lattice_shape(logical, block)
        if lattice != expected_lattice:
            raise GraphAdapterError("block_lattice_shape is inconsistent.")
        indices = _readonly_array(
            self.active_block_indices,
            np.int64,
            ndim=2,
            name="active_block_indices",
        )
        if indices.shape[1:] != (3,):
            raise GraphAdapterError("active_block_indices must have shape (n_blocks, 3).")
        flat = _readonly_array(
            self.active_block_flat_indices,
            np.int64,
            ndim=1,
            name="active_block_flat_indices",
        )
        if flat.shape != (indices.shape[0],):
            raise GraphAdapterError("active block coordinate and flat arrays must align.")
        if flat.size == 0:
            raise GraphAdapterError("A block-packing plan requires at least one block.")
        if flat.size > 1 and np.any(flat[1:] <= flat[:-1]):
            raise GraphAdapterError("Active blocks must be strictly lexicographically ordered.")
        reconstructed = np.column_stack(
            np.unravel_index(flat, lattice, order="C")
        ).astype(np.int64, copy=False)
        if not np.array_equal(reconstructed, indices):
            raise GraphAdapterError("Active block coordinates do not match flat indices.")
        nonzero = _positive_int(self.nonzero_node_count, name="nonzero_node_count")
        allocated = _positive_int(self.allocated_value_count, name="allocated_value_count")
        valid = _positive_int(self.valid_value_count, name="valid_value_count")
        partial = _positive_int(self.partial_block_count, name="partial_block_count", minimum=0)
        planning = _positive_int(self.planning_bytes, name="planning_bytes", minimum=0)
        expected_allocated = int(indices.shape[0]) * int(np.prod(block, dtype=object))
        if allocated != expected_allocated:
            raise GraphAdapterError("allocated_value_count is inconsistent with blocks.")
        if not nonzero <= valid <= allocated:
            raise GraphAdapterError("Block packing counts must satisfy nonzero <= valid <= allocated.")
        if partial > indices.shape[0]:
            raise GraphAdapterError("partial_block_count exceeds active block count.")
        object.__setattr__(self, "logical_grid_shape", logical)
        object.__setattr__(self, "block_shape", block)
        object.__setattr__(self, "block_lattice_shape", lattice)
        object.__setattr__(self, "active_block_indices", indices)
        object.__setattr__(self, "active_block_flat_indices", flat)
        object.__setattr__(self, "nonzero_node_count", nonzero)
        object.__setattr__(self, "allocated_value_count", allocated)
        object.__setattr__(self, "valid_value_count", valid)
        object.__setattr__(self, "partial_block_count", partial)
        object.__setattr__(self, "planning_bytes", planning)

    @property
    def active_block_count(self) -> int:
        return int(self.active_block_indices.shape[0])

    def to_json_dict(self, *, include_indices: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "logical_grid_shape": list(self.logical_grid_shape),
            "block_shape": list(self.block_shape),
            "block_lattice_shape": list(self.block_lattice_shape),
            "active_block_count": self.active_block_count,
            "nonzero_node_count": self.nonzero_node_count,
            "allocated_value_count": self.allocated_value_count,
            "valid_value_count": self.valid_value_count,
            "partial_block_count": self.partial_block_count,
            "planning_bytes": self.planning_bytes,
        }
        if include_indices:
            result["active_block_indices"] = self.active_block_indices.tolist()
            result["active_block_flat_indices"] = self.active_block_flat_indices.tolist()
        return result


def plan_block_packing(
    active_flat_indices: IntArray,
    *,
    logical_grid_shape: tuple[int, int, int],
    block_shape: tuple[int, int, int] = (16, 16, 16),
    max_nonzero_nodes: int | None = None,
    max_stored_block_values: int | None = None,
    max_blocks: int | None = None,
    max_planning_bytes: int | None = None,
) -> BlockPackingPlan:
    """Compute exact block ownership and counts before allocating block values."""

    logical = _shape3(logical_grid_shape, name="logical_grid_shape")
    block = _shape3(block_shape, name="block_shape")
    budget, _model, derived = resolve_density_resource_limits()
    nonzero_default = derived["max_density_nonzero_nodes"]
    nonzero_limit = (
        nonzero_default
        if max_nonzero_nodes is None
        else min(nonzero_default, _positive_int(max_nonzero_nodes, name="max_nonzero_nodes"))
    )
    stored_default = derived["max_density_stored_block_values"]
    stored_limit = (
        stored_default
        if max_stored_block_values is None
        else min(stored_default, _positive_int(max_stored_block_values, name="max_stored_block_values"))
    )
    block_default = derived["max_density_blocks"]
    block_limit = (
        block_default
        if max_blocks is None
        else min(block_default, _positive_int(max_blocks, name="max_blocks"))
    )
    planning_limit = (
        budget.max_memory_bytes
        if max_planning_bytes is None
        else min(_positive_int(max_planning_bytes, name="max_planning_bytes"), budget.max_memory_bytes)
    )
    flat = np.asarray(active_flat_indices, dtype=np.int64)
    logical_count = int(np.prod(logical, dtype=object))
    if flat.ndim != 1 or flat.size == 0:
        raise GraphAdapterError("active_flat_indices must be a nonempty vector.")
    if int(flat[0]) < 0 or int(flat[-1]) >= logical_count:
        raise GraphAdapterError("active_flat_indices lie outside the logical grid.")
    if flat.size > 1 and np.any(flat[1:] <= flat[:-1]):
        raise GraphAdapterError("active_flat_indices must be strictly increasing.")
    if flat.size > nonzero_limit:
        raise GraphComplexityError(
            f"Block packing requires {flat.size} nonzero nodes, exceeding "
            f"max_nonzero_nodes={nonzero_limit}."
        )

    # Coordinates, block coordinates, block IDs, stable unique workspace, and
    # terminal-validity accounting. This is a conservative package-owned bound.
    planning_upper = int(flat.size) * (3 * 8 + 3 * 8 + 8 + 8) + 8192
    if planning_upper > planning_limit:
        raise GraphComplexityError(
            f"Block packing requires at most {planning_upper} planning bytes, "
            f"exceeding max_planning_bytes={planning_limit}."
        )
    coordinates = np.column_stack(np.unravel_index(flat, logical, order="C")).astype(
        np.int64, copy=False
    )
    block_coordinates = coordinates // np.asarray(block, dtype=np.int64)[None, :]
    lattice = _block_lattice_shape(logical, block)
    block_ids_all = np.ravel_multi_index(
        (
            block_coordinates[:, 0],
            block_coordinates[:, 1],
            block_coordinates[:, 2],
        ),
        lattice,
        order="C",
    ).astype(np.int64, copy=False)
    block_ids = np.unique(block_ids_all).astype(np.int64, copy=False)
    if block_ids.size > block_limit:
        raise GraphComplexityError(
            f"Block packing requires {block_ids.size} blocks, exceeding "
            f"max_blocks={block_limit}."
        )
    block_indices = np.column_stack(
        np.unravel_index(block_ids, lattice, order="C")
    ).astype(np.int64, copy=False)
    block_volume = int(np.prod(block, dtype=object))
    allocated = int(block_ids.size) * block_volume
    if allocated > stored_limit:
        raise GraphComplexityError(
            f"Block packing requires {allocated} scalar slots, exceeding "
            f"max_stored_block_values={stored_limit}."
        )

    valid_count = 0
    partial_count = 0
    logical_array = np.asarray(logical, dtype=np.int64)
    block_array = np.asarray(block, dtype=np.int64)
    for block_index in block_indices:
        remaining = logical_array - block_index * block_array
        extents = np.minimum(block_array, remaining)
        valid = int(np.prod(extents, dtype=object))
        valid_count += valid
        if valid != block_volume:
            partial_count += 1

    return BlockPackingPlan(
        logical_grid_shape=logical,
        block_shape=block,
        block_lattice_shape=lattice,
        active_block_indices=block_indices,
        active_block_flat_indices=block_ids,
        nonzero_node_count=int(flat.size),
        allocated_value_count=allocated,
        valid_value_count=valid_count,
        partial_block_count=partial_count,
        planning_bytes=planning_upper,
    )


def plan_sparse_target_nodes(
    cic_masses: SparseCICNodeMasses3D,
    stencil: PeriodicGaussianStencilSupport,
    *,
    max_kernel_pairs: int,
    max_planning_bytes: int,
) -> IntArray:
    """Return exact sorted target nodes without constructing float field values."""

    if cic_masses.grid_shape != stencil.grid_shape:
        raise GraphAdapterError("CIC masses and stencil must share grid_shape.")
    budget, _model, derived = resolve_density_resource_limits()
    pair_limit = min(
        derived["max_density_kernel_pairs"],
        _positive_int(max_kernel_pairs, name="max_kernel_pairs"),
    )
    planning_limit = min(
        budget.max_memory_bytes,
        _positive_int(max_planning_bytes, name="max_planning_bytes"),
    )
    pair_count = cic_masses.occupied_node_count * stencil.stencil_offset_count
    if pair_count > pair_limit:
        raise GraphComplexityError(
            f"Sparse planning requires {pair_count} kernel pairs, exceeding "
            f"max_kernel_pairs={pair_limit}."
        )
    planning_upper = 24 * cic_masses.occupied_node_count + 16 * pair_count + 8192
    if planning_upper > planning_limit:
        raise GraphComplexityError(
            f"Sparse target planning requires at most {planning_upper} bytes, "
            f"exceeding max_planning_bytes={planning_limit}."
        )
    shape = cic_masses.grid_shape
    sources = np.column_stack(
        np.unravel_index(cic_masses.flat_indices, shape, order="C")
    ).astype(np.int64, copy=False)
    targets = np.empty(pair_count, dtype=np.int64)
    shape_array = np.asarray(shape, dtype=np.int64)
    cursor = 0
    for flat_offset in stencil.active_flat_indices:
        offset = np.asarray(
            np.unravel_index(int(flat_offset), shape, order="C"), dtype=np.int64
        )
        coordinates = np.mod(sources + offset[None, :], shape_array[None, :])
        count = sources.shape[0]
        targets[cursor : cursor + count] = np.ravel_multi_index(
            (coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]),
            shape,
            order="C",
        )
        cursor += count
    active = np.unique(targets).astype(np.int64, copy=False)
    active.setflags(write=False)
    return active


@dataclass(frozen=True, slots=True)
class PeriodicBlockScalarField3D:
    """Production fixed-block sparse scalar field on a periodic logical lattice."""

    field_key: str
    label: str
    physical_units: str
    logical_grid_shape: tuple[int, int, int]
    block_shape: tuple[int, int, int]
    active_block_indices: IntArray
    block_values: FloatArray
    block_valid_masks: BoolArray | None
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
    schema_version: str = PERIODIC_BLOCK_FIELD_SCHEMA
    smoothing_operator: str = DISCRETE_PERIODIZED_OPERATOR
    storage_backend: str = LOCAL_SPARSE_BACKEND

    def __post_init__(self) -> None:
        if self.schema_version != PERIODIC_BLOCK_FIELD_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported block-field schema {self.schema_version!r}."
            )
        if self.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR:
            raise GraphAdapterError(
                "PeriodicBlockScalarField3D requires discrete_periodized_v1."
            )
        if self.storage_backend != LOCAL_SPARSE_BACKEND:
            raise GraphAdapterError("storage_backend must be local_sparse.")
        for name in ("field_key", "label", "physical_units", "broadening_metric"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise GraphAdapterError(f"{name} must be a nonempty string.")
        logical = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        block = _shape3(self.block_shape, name="block_shape")
        lattice = _block_lattice_shape(logical, block)
        indices = _readonly_array(
            self.active_block_indices,
            np.int64,
            ndim=2,
            name="active_block_indices",
        )
        if indices.shape[1:] != (3,) or indices.shape[0] == 0:
            raise GraphAdapterError(
                "active_block_indices must have shape (n_blocks, 3) with n_blocks > 0."
            )
        if np.any(indices < 0) or np.any(indices >= np.asarray(lattice)[None, :]):
            raise GraphAdapterError("active_block_indices lie outside the block lattice.")
        block_ids = np.ravel_multi_index(
            (indices[:, 0], indices[:, 1], indices[:, 2]), lattice, order="C"
        )
        if block_ids.size > 1 and np.any(block_ids[1:] <= block_ids[:-1]):
            raise GraphAdapterError(
                "active_block_indices must be unique and lexicographically sorted."
            )
        values = _readonly_array(
            self.block_values,
            np.float64,
            ndim=4,
            name="block_values",
        )
        expected_shape = (indices.shape[0], *block)
        if values.shape != expected_shape:
            raise GraphAdapterError(
                f"block_values must have shape {expected_shape}; received {values.shape}."
            )
        if np.any(values < 0.0):
            raise GraphAdapterError("block_values must be nonnegative.")
        masks = None
        if self.block_valid_masks is not None:
            masks = _readonly_array(
                self.block_valid_masks,
                np.bool_,
                ndim=4,
                name="block_valid_masks",
            )
            if masks.shape != values.shape:
                raise GraphAdapterError("block_valid_masks must align with block_values.")
            if np.any(values[~masks] != 0.0):
                raise GraphAdapterError("Invalid partial-block slots must be exactly zero.")
        elif any(logical[a] % block[a] != 0 for a in range(3)):
            # Masks are required only when an active terminal block is partial.
            for block_index in indices:
                if np.any((block_index + 1) * np.asarray(block) > np.asarray(logical)):
                    raise GraphAdapterError(
                        "Partial active blocks require block_valid_masks."
                    )
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
            raise GraphAdapterError(
                "selected_atom_indices must be sorted, unique, and nonnegative."
            )
        samples = None
        if self.sample_positions is not None:
            samples = _readonly_array(
                self.sample_positions,
                np.float64,
                ndim=2,
                name="sample_positions",
            )
            if samples.shape[1:] != (3,):
                raise GraphAdapterError("sample_positions must have shape (n, 3).")
        metadata = freeze_json_mapping(self.metadata)
        object.__setattr__(self, "logical_grid_shape", logical)
        object.__setattr__(self, "block_shape", block)
        object.__setattr__(self, "active_block_indices", indices)
        object.__setattr__(self, "block_values", values)
        object.__setattr__(self, "block_valid_masks", masks)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "total_measure", total)
        object.__setattr__(self, "gaussian_bandwidth", sigma)
        object.__setattr__(self, "selected_atom_indices", atoms)
        object.__setattr__(self, "sample_positions", samples)
        object.__setattr__(self, "metadata", metadata)
        error = abs(self.integral - total)
        if error > 5.0e-13 * max(1.0, total):
            raise GraphAdapterError(
                "Block-sparse field is not normalized to total_measure: "
                f"error={error:.17g}."
            )

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.logical_grid_shape

    @property
    def block_lattice_shape(self) -> tuple[int, int, int]:
        return _block_lattice_shape(self.logical_grid_shape, self.block_shape)

    @property
    def voxel_volume(self) -> float:
        logical = int(np.prod(self.logical_grid_shape, dtype=object))
        return abs(float(np.linalg.det(self.display_cell))) / float(logical)

    def _valid_values(self) -> FloatArray:
        if self.block_valid_masks is None:
            return self.block_values.reshape(-1)
        return self.block_values[self.block_valid_masks]

    @property
    def integral(self) -> float:
        _, values = self._positive_flat_values()
        return float(np.sum(values, dtype=np.float64)) * self.voxel_volume

    def hdr_details(self, fraction: float) -> SparseHDRDetails:
        q = float(fraction)
        if not np.isfinite(q) or not 0.0 < q < 1.0:
            raise GraphStyleError("fraction must lie strictly between zero and one.")
        _, positive = self._positive_flat_values()
        descending = np.sort(positive)[::-1]
        cumulative = np.cumsum(descending, dtype=np.float64) * self.voxel_volume
        index = min(
            int(np.searchsorted(cumulative, q * self.total_measure, side="left")),
            descending.size - 1,
        )
        threshold = float(descending[index])
        selected = positive >= threshold
        measure = float(np.sum(positive[selected], dtype=np.float64)) * self.voxel_volume
        return SparseHDRDetails(
            requested_mass_fraction=q,
            threshold=threshold,
            achieved_mass_fraction=measure / self.total_measure,
            selected_node_count=int(np.count_nonzero(selected)),
            threshold_tie_count=int(np.count_nonzero(positive == threshold)),
            selected_measure=measure,
            total_measure=self.total_measure,
        )

    def threshold_for_mass_fraction(self, q: float) -> float:
        return self.hdr_details(q).threshold

    def storage_summary(self) -> DensityStorageSummary:
        mask_bytes = 0 if self.block_valid_masks is None else int(self.block_valid_masks.nbytes)
        realized = int(
            self.active_block_indices.nbytes + self.block_values.nbytes + mask_bytes
        )
        valid = self._valid_values()
        return DensityStorageSummary(
            storage_backend=LOCAL_SPARSE_BACKEND,
            logical_grid_shape=self.logical_grid_shape,
            logical_node_count=int(np.prod(self.logical_grid_shape, dtype=object)),
            nonzero_node_count=int(np.count_nonzero(valid)),
            stored_value_count=int(self.block_values.size),
            stored_block_count=int(self.active_block_indices.shape[0]),
            estimated_bytes=realized,
            realized_bytes=realized,
            metadata={
                "representation": "fixed_block_sparse",
                "block_shape": list(self.block_shape),
                "block_lattice_shape": list(self.block_lattice_shape),
                "valid_value_count": int(valid.size),
                "partial_masks_present": self.block_valid_masks is not None,
                "index_dtype": "int64",
                "value_dtype": "float64",
            },
        )

    def _positive_flat_values(self) -> tuple[IntArray, FloatArray]:
        flat_parts: list[IntArray] = []
        value_parts: list[FloatArray] = []
        logical = self.logical_grid_shape
        block = self.block_shape
        for row, block_index in enumerate(self.active_block_indices):
            local = np.argwhere(self.block_values[row] > 0.0).astype(np.int64, copy=False)
            if local.size == 0:
                continue
            global_indices = block_index[None, :] * np.asarray(block)[None, :] + local
            inside = np.all(global_indices < np.asarray(logical)[None, :], axis=1)
            global_indices = global_indices[inside]
            local = local[inside]
            flat = np.ravel_multi_index(
                (global_indices[:, 0], global_indices[:, 1], global_indices[:, 2]),
                logical,
                order="C",
            ).astype(np.int64, copy=False)
            values = self.block_values[row, local[:, 0], local[:, 1], local[:, 2]]
            flat_parts.append(flat)
            value_parts.append(values)
        if not flat_parts:
            raise GraphAdapterError("A normalized sparse field has no positive nodes.")
        flat_all = np.concatenate(flat_parts).astype(np.int64, copy=False)
        values_all = np.concatenate(value_parts).astype(np.float64, copy=False)
        order = np.argsort(flat_all, kind="stable")
        flat_sorted = np.array(flat_all[order], dtype=np.int64, copy=True, order="C")
        values_sorted = np.array(values_all[order], dtype=np.float64, copy=True, order="C")
        if flat_sorted.size > 1 and np.any(flat_sorted[1:] <= flat_sorted[:-1]):
            raise GraphAdapterError("Block storage contains duplicate logical nodes.")
        flat_sorted.setflags(write=False)
        values_sorted.setflags(write=False)
        return flat_sorted, values_sorted

    def iter_stored_nodes(
        self,
        *,
        batch_size: int | None = None,
    ) -> Iterator[tuple[IntArray, FloatArray]]:
        flat, values = self._positive_flat_values()
        size = int(flat.size) if batch_size is None else _positive_int(
            batch_size, name="batch_size"
        )
        for start in range(0, int(flat.size), size):
            stop = min(int(flat.size), start + size)
            coordinates = np.column_stack(
                np.unravel_index(flat[start:stop], self.logical_grid_shape, order="C")
            ).astype(np.int64, copy=False)
            coordinates = np.array(coordinates, dtype=np.int64, copy=True, order="C")
            batch_values = np.array(values[start:stop], dtype=np.float64, copy=True, order="C")
            coordinates.setflags(write=False)
            batch_values.setflags(write=False)
            yield coordinates, batch_values

    def gather_node_values(self, logical_indices: IntArray) -> FloatArray:
        indices = np.asarray(logical_indices)
        if indices.ndim != 2 or indices.shape[1:] != (3,):
            raise GraphAdapterError("logical_indices must have shape (n, 3).")
        if not np.issubdtype(indices.dtype, np.integer):
            raise GraphAdapterError("logical_indices must contain integers.")
        canonical = np.mod(
            indices.astype(np.int64, copy=False),
            np.asarray(self.logical_grid_shape, dtype=np.int64)[None, :],
        )
        block_indices = canonical // np.asarray(self.block_shape, dtype=np.int64)[None, :]
        local = canonical % np.asarray(self.block_shape, dtype=np.int64)[None, :]
        block_ids = np.ravel_multi_index(
            (block_indices[:, 0], block_indices[:, 1], block_indices[:, 2]),
            self.block_lattice_shape,
            order="C",
        ).astype(np.int64, copy=False)
        active_ids = np.ravel_multi_index(
            (
                self.active_block_indices[:, 0],
                self.active_block_indices[:, 1],
                self.active_block_indices[:, 2],
            ),
            self.block_lattice_shape,
            order="C",
        ).astype(np.int64, copy=False)
        positions = np.searchsorted(active_ids, block_ids)
        result = np.zeros(indices.shape[0], dtype=np.float64)
        valid = positions < active_ids.size
        query_rows = np.nonzero(valid)[0]
        if query_rows.size:
            matched = active_ids[positions[query_rows]] == block_ids[query_rows]
            query_rows = query_rows[matched]
            block_rows = positions[query_rows]
            result[query_rows] = self.block_values[
                block_rows,
                local[query_rows, 0],
                local[query_rows, 1],
                local[query_rows, 2],
            ]
        result.setflags(write=False)
        return result

    def to_dense_values(
        self,
        *,
        max_nodes: int | None = None,
    ) -> FloatArray:
        _budget, _model, derived = resolve_density_resource_limits()
        default_limit = derived["max_density_voxels"]
        limit = (
            default_limit
            if max_nodes is None
            else min(default_limit, _positive_int(max_nodes, name="max_nodes"))
        )
        logical_count = int(np.prod(self.logical_grid_shape, dtype=object))
        if logical_count > limit:
            raise GraphComplexityError(
                f"Dense block-field conversion requires {logical_count} nodes, "
                f"exceeding max_nodes={limit}."
            )
        dense = np.zeros(logical_count, dtype=np.float64)
        flat, values = self._positive_flat_values()
        dense[flat] = values
        dense = dense.reshape(self.logical_grid_shape)
        dense.setflags(write=False)
        return dense

    def to_json_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "label": self.label,
            "physical_units": self.physical_units,
            "logical_grid_shape": list(self.logical_grid_shape),
            "block_shape": list(self.block_shape),
            "active_block_indices": self.active_block_indices.tolist(),
            "display_cell": self.display_cell.tolist(),
            "total_measure": self.total_measure,
            "gaussian_bandwidth": self.gaussian_bandwidth,
            "smoothing_operator": self.smoothing_operator,
            "broadening_metric": self.broadening_metric,
            "storage_backend": self.storage_backend,
            "source_provenance": self.source_provenance.to_json_dict(),
            "selected_atom_indices": list(self.selected_atom_indices),
            "sample_positions": (
                None if self.sample_positions is None else self.sample_positions.tolist()
            ),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_values:
            result["block_values"] = self.block_values.tolist()
            result["block_valid_masks"] = (
                None
                if self.block_valid_masks is None
                else self.block_valid_masks.tolist()
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "PeriodicBlockScalarField3D":
        if value.get("storage_backend") != LOCAL_SPARSE_BACKEND:
            raise GraphAdapterError(
                "PeriodicBlockScalarField3D requires storage_backend='local_sparse'."
            )
        if "block_values" not in value:
            raise GraphAdapterError("Block-field JSON requires block_values.")
        masks = value.get("block_valid_masks")
        return cls(
            schema_version=str(value["schema_version"]),
            field_key=str(value["field_key"]),
            label=str(value["label"]),
            physical_units=str(value["physical_units"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            block_shape=tuple(value["block_shape"]),
            active_block_indices=np.asarray(value["active_block_indices"], dtype=np.int64),
            block_values=np.asarray(value["block_values"], dtype=np.float64),
            block_valid_masks=(
                None if masks is None else np.asarray(masks, dtype=np.bool_)
            ),
            display_cell=np.asarray(value["display_cell"], dtype=np.float64),
            total_measure=float(value["total_measure"]),
            gaussian_bandwidth=float(value["gaussian_bandwidth"]),
            smoothing_operator=str(value["smoothing_operator"]),
            broadening_metric=str(value["broadening_metric"]),
            storage_backend=str(value["storage_backend"]),
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
        )


def pack_sparse_reference_blocks(
    reference: SparseCanonicalDensityReference3D,
    *,
    block_shape: tuple[int, int, int] = (16, 16, 16),
    selected_atom_indices: tuple[int, ...] = (),
    sample_positions: FloatArray | None = None,
    max_nonzero_nodes: int | None = None,
    max_stored_block_values: int | None = None,
    max_blocks: int | None = None,
    max_planning_bytes: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> PeriodicBlockScalarField3D:
    """Pack one LD1-A field into deterministic production blocks."""

    if not isinstance(reference, SparseCanonicalDensityReference3D):
        raise TypeError("reference must be SparseCanonicalDensityReference3D.")
    plan = plan_block_packing(
        reference.active_flat_indices,
        logical_grid_shape=reference.logical_grid_shape,
        block_shape=block_shape,
        max_nonzero_nodes=max_nonzero_nodes,
        max_stored_block_values=max_stored_block_values,
        max_blocks=max_blocks,
        max_planning_bytes=max_planning_bytes,
    )
    values = np.zeros(
        (plan.active_block_count, *plan.block_shape), dtype=np.float64, order="C"
    )
    coordinates = np.column_stack(
        np.unravel_index(
            reference.active_flat_indices, reference.logical_grid_shape, order="C"
        )
    ).astype(np.int64, copy=False)
    block_coordinates = coordinates // np.asarray(plan.block_shape, dtype=np.int64)[None, :]
    local = coordinates % np.asarray(plan.block_shape, dtype=np.int64)[None, :]
    block_ids = np.ravel_multi_index(
        (
            block_coordinates[:, 0],
            block_coordinates[:, 1],
            block_coordinates[:, 2],
        ),
        plan.block_lattice_shape,
        order="C",
    ).astype(np.int64, copy=False)
    rows = np.searchsorted(plan.active_block_flat_indices, block_ids)
    values[rows, local[:, 0], local[:, 1], local[:, 2]] = reference.active_values

    masks = None
    if plan.partial_block_count:
        masks = np.zeros(values.shape, dtype=np.bool_, order="C")
        logical = np.asarray(plan.logical_grid_shape, dtype=np.int64)
        block = np.asarray(plan.block_shape, dtype=np.int64)
        for row, block_index in enumerate(plan.active_block_indices):
            extents = np.minimum(block, logical - block_index * block)
            masks[row, : extents[0], : extents[1], : extents[2]] = True

    field_metadata = {
        **reference.metadata.to_json_dict(),
        "block_packing": plan.to_json_dict(include_indices=False),
        "representation": "fixed_block_sparse",
        "production_backend": True,
        "reference_schema_version": reference.schema_version,
        **({} if metadata is None else dict(metadata)),
    }
    return PeriodicBlockScalarField3D(
        field_key=reference.field_key,
        label=reference.label,
        physical_units=reference.physical_units,
        logical_grid_shape=reference.logical_grid_shape,
        block_shape=plan.block_shape,
        active_block_indices=plan.active_block_indices,
        block_values=values,
        block_valid_masks=masks,
        display_cell=reference.display_cell,
        total_measure=reference.total_measure,
        gaussian_bandwidth=reference.gaussian_bandwidth,
        broadening_metric=reference.broadening_metric,
        source_provenance=reference.source_provenance,
        selected_atom_indices=selected_atom_indices,
        sample_positions=sample_positions,
        metadata=field_metadata,
    )
