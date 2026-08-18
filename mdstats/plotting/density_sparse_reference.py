"""Deterministic sparse CIC and canonical-convolution reference path.

This module implements architecture gate LD1-A.  Periodic trilinear
cloud-in-cell (CIC) assignment follows Hockney and Eastwood, *Computer
Simulation Using Particles* (1988).  Highest-density-region thresholds follow
Hyndman, *The American Statistician* 50, 120-126 (1996).  The finite-support
``discrete_periodized_v1`` stencil and all sparse accumulation, normalization,
and resource policies are project-specific mdstats definitions.

The reference representation stores sorted logical flat indices and values.  It
is deliberately not the production block-sparse backend; block packing belongs
to LD1-B.  The implementation is retained as a simple numerical oracle for all
later optimized sparse paths.
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
    PeriodicWeightedSamples3D,
    freeze_json_mapping,
)
from .density_kernel import (
    PeriodicGaussianStencilSupport,
    build_periodic_gaussian_stencil_support,
)
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

SPARSE_CIC_MASSES_SCHEMA = "mdstats.sparse-cic-node-masses.v1"
SPARSE_HDR_DETAILS_SCHEMA = "mdstats.sparse-hdr-details.v1"
SPARSE_REFERENCE_FIELD_SCHEMA = "mdstats.sparse-canonical-reference-field.v1"

DEFAULT_MAX_CIC_CONTRIBUTIONS = 20_000_000
DEFAULT_MAX_KERNEL_PAIRS = 50_000_000
DEFAULT_MAX_WORKSPACE_BYTES = 2_000_000_000
DEFAULT_MAX_DENSE_DEBUG_NODES = 16_777_216


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


def _validated_shape(value: Any) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphAdapterError("grid_shape must contain three entries.")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, np.integer)):
            raise GraphAdapterError("grid_shape entries must be positive integers.")
        integer = int(item)
        if integer <= 0:
            raise GraphAdapterError("grid_shape entries must be positive integers.")
        result.append(integer)
    return tuple(result)  # type: ignore[return-value]


def _validated_cell(value: Any) -> FloatArray:
    cell = np.asarray(value, dtype=np.float64)
    if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
        raise GraphAdapterError("display_cell must be a finite 3x3 matrix.")
    determinant = float(np.linalg.det(cell))
    scale = max(1.0, float(np.linalg.norm(cell, ord=np.inf)) ** 3)
    if abs(determinant) <= 64.0 * np.finfo(np.float64).eps * scale:
        raise GraphAdapterError("display_cell must be nonsingular.")
    result = np.array(cell, dtype=np.float64, copy=True, order="C")
    result.setflags(write=False)
    return result


def _positive_limit(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _validate_flat_sparse_vectors(
    flat_indices: Any,
    values: Any,
    *,
    logical_node_count: int,
    value_name: str,
) -> tuple[IntArray, FloatArray]:
    indices = _readonly_array(flat_indices, np.int64, ndim=1, name="flat_indices")
    vector = _readonly_array(values, np.float64, ndim=1, name=value_name)
    if indices.shape != vector.shape:
        raise GraphAdapterError(f"flat_indices and {value_name} must align.")
    if indices.size == 0:
        raise GraphAdapterError("Sparse vectors must contain at least one node.")
    if int(indices[0]) < 0 or int(indices[-1]) >= logical_node_count:
        raise GraphAdapterError("Sparse flat indices lie outside the logical grid.")
    if indices.size > 1 and np.any(indices[1:] <= indices[:-1]):
        raise GraphAdapterError("Sparse flat indices must be strictly increasing.")
    if np.any(vector <= 0.0):
        raise GraphAdapterError(f"{value_name} must be strictly positive.")
    return indices, vector


@dataclass(frozen=True, slots=True)
class SparseCICNodeMasses3D:
    """Sorted occupied logical nodes after deterministic periodic CIC assignment."""

    grid_shape: tuple[int, int, int]
    flat_indices: IntArray
    node_masses: FloatArray
    total_measure: float
    source_provenance: DensitySourceProvenance
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = SPARSE_CIC_MASSES_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_CIC_MASSES_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported sparse-CIC schema {self.schema_version!r}."
            )
        shape = _validated_shape(self.grid_shape)
        logical = int(np.prod(shape, dtype=object))
        indices, masses = _validate_flat_sparse_vectors(
            self.flat_indices,
            self.node_masses,
            logical_node_count=logical,
            value_name="node_masses",
        )
        total = float(self.total_measure)
        if not np.isfinite(total) or total <= 0.0:
            raise GraphAdapterError("total_measure must be finite and positive.")
        deposited = float(np.sum(masses, dtype=np.float64))
        tolerance = 5.0e-13 * max(1.0, total)
        if abs(deposited - total) > tolerance:
            raise GraphAdapterError(
                "Sparse CIC masses do not conserve total_measure within tolerance: "
                f"deposited={deposited:.17g}, target={total:.17g}."
            )
        if not isinstance(self.source_provenance, DensitySourceProvenance):
            raise TypeError("source_provenance must be DensitySourceProvenance.")
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "flat_indices", indices)
        object.__setattr__(self, "node_masses", masses)
        object.__setattr__(self, "total_measure", total)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def occupied_node_count(self) -> int:
        return int(self.flat_indices.size)

    @property
    def deposited_measure(self) -> float:
        return float(np.sum(self.node_masses, dtype=np.float64))

    def to_dense_mass_grid(
        self,
        *,
        max_nodes: int | None = None,
    ) -> FloatArray:
        """Materialize a dense mass grid only for bounded debugging cases."""

        _budget, _model, derived = resolve_density_resource_limits()
        default_limit = derived["max_density_voxels"]
        limit = (
            default_limit
            if max_nodes is None
            else min(default_limit, _positive_limit(max_nodes, name="max_nodes"))
        )
        logical = int(np.prod(self.grid_shape, dtype=object))
        if logical > limit:
            raise GraphComplexityError(
                f"Dense CIC debugging requires {logical} nodes, exceeding "
                f"max_nodes={limit}."
            )
        dense = np.zeros(logical, dtype=np.float64)
        dense[self.flat_indices] = self.node_masses
        dense = dense.reshape(self.grid_shape)
        dense.setflags(write=False)
        return dense


@dataclass(frozen=True, slots=True)
class SparseHDRDetails:
    """Auditable highest-density-region threshold and tie information."""

    requested_mass_fraction: float
    threshold: float
    achieved_mass_fraction: float
    selected_node_count: int
    threshold_tie_count: int
    selected_measure: float
    total_measure: float
    schema_version: str = SPARSE_HDR_DETAILS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_HDR_DETAILS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported sparse-HDR schema {self.schema_version!r}."
            )
        requested = float(self.requested_mass_fraction)
        threshold = float(self.threshold)
        achieved = float(self.achieved_mass_fraction)
        selected = float(self.selected_measure)
        total = float(self.total_measure)
        if not 0.0 < requested < 1.0:
            raise GraphStyleError("requested_mass_fraction must lie in (0, 1).")
        if not np.isfinite(threshold) or threshold <= 0.0:
            raise GraphAdapterError("threshold must be finite and positive.")
        if not np.isfinite(achieved) or not requested <= achieved <= 1.0 + 5.0e-13:
            raise GraphAdapterError("achieved_mass_fraction is inconsistent.")
        if not np.isfinite(selected) or selected <= 0.0:
            raise GraphAdapterError("selected_measure must be finite and positive.")
        if not np.isfinite(total) or total <= 0.0:
            raise GraphAdapterError("total_measure must be finite and positive.")
        selected_count = _positive_limit(
            self.selected_node_count, name="selected_node_count"
        )
        tie_count = _positive_limit(
            self.threshold_tie_count, name="threshold_tie_count"
        )
        if tie_count > selected_count:
            raise GraphAdapterError(
                "threshold_tie_count cannot exceed selected_node_count."
            )
        object.__setattr__(self, "requested_mass_fraction", requested)
        object.__setattr__(self, "threshold", threshold)
        object.__setattr__(self, "achieved_mass_fraction", min(1.0, achieved))
        object.__setattr__(self, "selected_node_count", selected_count)
        object.__setattr__(self, "threshold_tie_count", tie_count)
        object.__setattr__(self, "selected_measure", selected)
        object.__setattr__(self, "total_measure", total)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "requested_mass_fraction": self.requested_mass_fraction,
            "threshold": self.threshold,
            "achieved_mass_fraction": self.achieved_mass_fraction,
            "selected_node_count": self.selected_node_count,
            "threshold_tie_count": self.threshold_tie_count,
            "selected_measure": self.selected_measure,
            "total_measure": self.total_measure,
        }


@dataclass(frozen=True, slots=True)
class SparseCanonicalDensityReference3D:
    """Flat-node sparse reference field for ``discrete_periodized_v1``."""

    field_key: str
    label: str
    physical_units: str
    logical_grid_shape: tuple[int, int, int]
    active_flat_indices: IntArray
    active_values: FloatArray
    display_cell: FloatArray
    total_measure: float
    gaussian_bandwidth: float
    broadening_metric: str
    source_provenance: DensitySourceProvenance
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = SPARSE_REFERENCE_FIELD_SCHEMA
    smoothing_operator: str = DISCRETE_PERIODIZED_OPERATOR
    storage_backend: str = LOCAL_SPARSE_BACKEND

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_REFERENCE_FIELD_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported sparse-reference schema {self.schema_version!r}."
            )
        if self.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR:
            raise GraphAdapterError(
                "SparseCanonicalDensityReference3D requires discrete_periodized_v1."
            )
        if self.storage_backend != LOCAL_SPARSE_BACKEND:
            raise GraphAdapterError("storage_backend must be local_sparse.")
        for name in ("field_key", "label", "physical_units", "broadening_metric"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise GraphAdapterError(f"{name} must be a nonempty string.")
        shape = _validated_shape(self.logical_grid_shape)
        logical = int(np.prod(shape, dtype=object))
        indices, values = _validate_flat_sparse_vectors(
            self.active_flat_indices,
            self.active_values,
            logical_node_count=logical,
            value_name="active_values",
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
        integral = float(np.sum(values, dtype=np.float64)) * (
            abs(float(np.linalg.det(cell))) / float(logical)
        )
        if abs(integral - total) > 5.0e-13 * max(1.0, total):
            raise GraphAdapterError(
                "Sparse reference field is not normalized to total_measure."
            )
        object.__setattr__(self, "logical_grid_shape", shape)
        object.__setattr__(self, "active_flat_indices", indices)
        object.__setattr__(self, "active_values", values)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "total_measure", total)
        object.__setattr__(self, "gaussian_bandwidth", sigma)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def grid_shape(self) -> tuple[int, int, int]:
        return self.logical_grid_shape

    @property
    def voxel_volume(self) -> float:
        logical = int(np.prod(self.logical_grid_shape, dtype=object))
        return abs(float(np.linalg.det(self.display_cell))) / float(logical)

    @property
    def integral(self) -> float:
        return float(np.sum(self.active_values, dtype=np.float64)) * self.voxel_volume

    def hdr_details(self, fraction: float) -> SparseHDRDetails:
        q = float(fraction)
        if not np.isfinite(q) or not 0.0 < q < 1.0:
            raise GraphStyleError("fraction must lie strictly between zero and one.")
        descending = np.sort(self.active_values)[::-1]
        cumulative_measure = np.cumsum(descending, dtype=np.float64) * self.voxel_volume
        index = int(
            np.searchsorted(
                cumulative_measure,
                q * self.total_measure,
                side="left",
            )
        )
        index = min(index, descending.size - 1)
        threshold = float(descending[index])
        selected_mask = self.active_values >= threshold
        selected_measure = float(
            np.sum(self.active_values[selected_mask], dtype=np.float64)
            * self.voxel_volume
        )
        return SparseHDRDetails(
            requested_mass_fraction=q,
            threshold=threshold,
            achieved_mass_fraction=selected_measure / self.total_measure,
            selected_node_count=int(np.count_nonzero(selected_mask)),
            threshold_tie_count=int(np.count_nonzero(self.active_values == threshold)),
            selected_measure=selected_measure,
            total_measure=self.total_measure,
        )

    def threshold_for_mass_fraction(self, q: float) -> float:
        return self.hdr_details(q).threshold

    def storage_summary(self) -> DensityStorageSummary:
        count = int(self.active_flat_indices.size)
        bytes_ = int(self.active_flat_indices.nbytes + self.active_values.nbytes)
        return DensityStorageSummary(
            storage_backend=LOCAL_SPARSE_BACKEND,
            logical_grid_shape=self.logical_grid_shape,
            logical_node_count=int(np.prod(self.logical_grid_shape, dtype=object)),
            nonzero_node_count=count,
            stored_value_count=count,
            stored_block_count=0,
            estimated_bytes=bytes_,
            realized_bytes=bytes_,
            metadata={
                "representation": "flat_node_reference",
                "production_backend": False,
                "index_dtype": "int64",
                "value_dtype": "float64",
            },
        )

    def iter_stored_nodes(
        self,
        *,
        batch_size: int | None = None,
    ) -> Iterator[tuple[IntArray, FloatArray]]:
        size = (
            int(self.active_flat_indices.size)
            if batch_size is None
            else _positive_limit(batch_size, name="batch_size")
        )
        shape = self.logical_grid_shape
        for start in range(0, int(self.active_flat_indices.size), size):
            stop = min(int(self.active_flat_indices.size), start + size)
            flat = self.active_flat_indices[start:stop]
            coordinates = np.column_stack(
                np.unravel_index(flat, shape, order="C")
            ).astype(np.int64, copy=False)
            coordinates = np.array(coordinates, dtype=np.int64, copy=True, order="C")
            values = np.array(
                self.active_values[start:stop],
                dtype=np.float64,
                copy=True,
                order="C",
            )
            coordinates.setflags(write=False)
            values.setflags(write=False)
            yield coordinates, values

    def gather_node_values(self, logical_indices: IntArray) -> FloatArray:
        indices = np.asarray(logical_indices, dtype=np.int64)
        if indices.ndim != 2 or indices.shape[1:] != (3,):
            raise GraphAdapterError("logical_indices must have shape (n, 3).")
        shape_array = np.asarray(self.logical_grid_shape, dtype=np.int64)
        canonical = np.mod(indices, shape_array[None, :])
        flat = np.ravel_multi_index(
            (canonical[:, 0], canonical[:, 1], canonical[:, 2]),
            self.logical_grid_shape,
            order="C",
        ).astype(np.int64, copy=False)
        positions = np.searchsorted(self.active_flat_indices, flat)
        result = np.zeros(flat.shape, dtype=np.float64)
        valid = positions < self.active_flat_indices.size
        valid_indices = np.nonzero(valid)[0]
        if valid_indices.size:
            matched = (
                self.active_flat_indices[positions[valid_indices]]
                == flat[valid_indices]
            )
            selected = valid_indices[matched]
            result[selected] = self.active_values[positions[selected]]
        result.setflags(write=False)
        return result

    def to_dense_values(
        self,
        *,
        max_nodes: int | None = None,
    ) -> FloatArray:
        """Materialize dense values for bounded debugging and oracle comparisons."""

        _budget, _model, derived = resolve_density_resource_limits()
        default_limit = derived["max_density_voxels"]
        limit = (
            default_limit
            if max_nodes is None
            else min(default_limit, _positive_limit(max_nodes, name="max_nodes"))
        )
        logical = int(np.prod(self.logical_grid_shape, dtype=object))
        if logical > limit:
            raise GraphComplexityError(
                f"Dense sparse-reference conversion requires {logical} nodes, "
                f"exceeding max_nodes={limit}."
            )
        dense = np.zeros(logical, dtype=np.float64)
        dense[self.active_flat_indices] = self.active_values
        dense = dense.reshape(self.logical_grid_shape)
        dense.setflags(write=False)
        return dense


def estimate_periodic_cic_sparse_workspace_bytes(sample_count: int) -> int:
    """Return the conservative package-owned CIC workspace upper bound.

    The bound is shared by the reference and optimized deterministic CIC
    implementations and is intentionally execution-only.  PAR-DENS6 uses the
    same estimate in Phase-B task contracts so the global scheduler accounts
    for the deposition workspace that is rebuilt during realization.
    """

    count = _positive_limit(sample_count, name="sample_count")
    contribution_upper = 8 * count
    return int(128 * contribution_upper + 128 * count + 4096)


def aggregate_periodic_cic_sparse(
    samples: PeriodicWeightedSamples3D,
    grid_shape: tuple[int, int, int],
    *,
    max_cic_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
) -> SparseCICNodeMasses3D:
    """Aggregate periodic CIC contributions in deterministic offset-major order."""

    if not isinstance(samples, PeriodicWeightedSamples3D):
        raise TypeError("samples must be PeriodicWeightedSamples3D.")
    shape = _validated_shape(grid_shape)
    budget, _model, derived = resolve_density_resource_limits()
    contribution_default = derived["max_density_kernel_pairs"]
    contribution_limit = (
        contribution_default
        if max_cic_contributions is None
        else min(contribution_default, _positive_limit(max_cic_contributions, name="max_cic_contributions"))
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_limit(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    sample_count = int(samples.fractional_positions.shape[0])
    contribution_upper = 8 * sample_count
    if contribution_upper > contribution_limit:
        raise GraphComplexityError(
            "Sparse CIC aggregation requires at most "
            f"{contribution_upper} contributions, exceeding "
            f"max_cic_contributions={contribution_limit}."
        )
    # Conservative bound includes contribution vectors, stable-sort order, sorted
    # copies, source geometry, and reduced output vectors.
    workspace_upper = estimate_periodic_cic_sparse_workspace_bytes(sample_count)
    if workspace_upper > workspace_limit:
        raise GraphComplexityError(
            "Sparse CIC aggregation requires at most "
            f"{workspace_upper} bytes of package-owned workspace, exceeding "
            f"max_workspace_bytes={workspace_limit}."
        )

    fractional = samples.fractional_positions
    folded = fractional - np.floor(fractional)
    scale = np.asarray(shape, dtype=np.float64)
    scaled = folded * scale[None, :]
    base = np.floor(scaled).astype(np.int64)
    delta = scaled - base

    flat_parts: list[IntArray] = []
    mass_parts: list[FloatArray] = []
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
                if not np.any(mask):
                    continue
                flat = np.ravel_multi_index(
                    (ix[mask], iy[mask], iz[mask]), shape, order="C"
                ).astype(np.int64, copy=False)
                flat_parts.append(flat)
                mass_parts.append(contribution[mask])

    if not flat_parts:
        raise GraphAdapterError("Positive weighted samples produced no CIC mass.")
    flat_all = np.concatenate(flat_parts).astype(np.int64, copy=False)
    mass_all = np.concatenate(mass_parts).astype(np.float64, copy=False)
    # The geometry and per-offset part lists are dead before unique/inverse
    # construction.  Releasing them lowers peak RSS without changing the
    # deterministic accumulation sequence.
    del folded, scaled, base, delta, scale, flat_parts, mass_parts
    del wx, ix, wy, iy, wz, iz, contribution, mask
    unique_flat = np.unique(flat_all).astype(np.int64, copy=False)
    inverse = np.searchsorted(unique_flat, flat_all)
    reduced_mass = np.zeros(unique_flat.size, dtype=np.float64)
    # Preserve the dense offset-major/sample-major CIC accumulation order.
    np.add.at(reduced_mass, inverse, mass_all)
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
            "positive_contribution_count": int(mass_all.size),
            "contribution_upper_bound": contribution_upper,
            "occupied_node_count": int(unique_flat.size),
            "deposited_measure_before_smoothing": deposited,
            "deposition_measure_error": error,
            "deterministic_accumulation_order": "offset_major_then_sample_stable",
            "workspace_upper_bound_bytes": workspace_upper,
        },
    )


def scatter_periodic_stencil_sparse(
    cic_masses: SparseCICNodeMasses3D,
    stencil: PeriodicGaussianStencilSupport,
    *,
    field_key: str,
    label: str,
    physical_units: str,
    broadening_metric: str,
    max_kernel_pairs: int | None = None,
    max_workspace_bytes: int | None = None,
) -> SparseCanonicalDensityReference3D:
    """Scatter one canonical support in stencil-major deterministic order."""

    if not isinstance(cic_masses, SparseCICNodeMasses3D):
        raise TypeError("cic_masses must be SparseCICNodeMasses3D.")
    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    if cic_masses.grid_shape != stencil.grid_shape:
        raise GraphAdapterError("CIC masses and stencil must share grid_shape.")
    budget, _model, derived = resolve_density_resource_limits()
    pair_default = derived["max_density_kernel_pairs"]
    pair_limit = (
        pair_default
        if max_kernel_pairs is None
        else min(pair_default, _positive_limit(max_kernel_pairs, name="max_kernel_pairs"))
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_limit(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    occupied = cic_masses.occupied_node_count
    stencil_count = stencil.stencil_offset_count
    pair_count = occupied * stencil_count
    if pair_count > pair_limit:
        raise GraphComplexityError(
            "Sparse canonical scatter requires "
            f"{pair_count} kernel pairs, exceeding max_kernel_pairs={pair_limit}."
        )
    # Conservative bound covers target/value vectors, stable-sort order, sorted
    # copies, source coordinates, masks, and reduced output vectors.
    workspace_upper = 128 * pair_count + 128 * occupied + 4096
    if workspace_upper > workspace_limit:
        raise GraphComplexityError(
            "Sparse canonical scatter requires at most "
            f"{workspace_upper} bytes of package-owned workspace, exceeding "
            f"max_workspace_bytes={workspace_limit}."
        )

    shape = cic_masses.grid_shape
    source_coordinates = np.column_stack(
        np.unravel_index(cic_masses.flat_indices, shape, order="C")
    ).astype(np.int64, copy=False)
    target_flat = np.empty(pair_count, dtype=np.int64)
    pair_values = np.empty(pair_count, dtype=np.float64)
    cursor = 0
    shape_array = np.asarray(shape, dtype=np.int64)
    # Stencil-major order matches the direct dense convolution's accumulation
    # order as closely as possible while remaining sparse and deterministic.
    for flat_offset, weight in zip(
        stencil.active_flat_indices,
        stencil.active_weights,
        strict=True,
    ):
        offset = np.asarray(
            np.unravel_index(int(flat_offset), shape, order="C"),
            dtype=np.int64,
        )
        targets = np.mod(source_coordinates + offset[None, :], shape_array[None, :])
        count = occupied
        target_flat[cursor : cursor + count] = np.ravel_multi_index(
            (targets[:, 0], targets[:, 1], targets[:, 2]), shape, order="C"
        )
        pair_values[cursor : cursor + count] = (
            cic_masses.node_masses * float(weight)
        )
        cursor += count
    if cursor != pair_count:
        raise AssertionError("Internal sparse scatter pair-count mismatch.")

    active_flat = np.unique(target_flat).astype(np.int64, copy=False)
    inverse = np.searchsorted(active_flat, target_flat)
    node_masses = np.zeros(active_flat.size, dtype=np.float64)
    # Pair generation is stencil-major, so np.add.at matches dense direct
    # convolution's per-offset accumulation order for every target node.
    np.add.at(node_masses, inverse, pair_values)
    positive = node_masses > 0.0
    active_flat = active_flat[positive]
    node_masses = node_masses[positive]
    raw_measure = float(np.sum(node_masses, dtype=np.float64))
    if not np.isfinite(raw_measure) or raw_measure <= 0.0:
        raise GraphAdapterError("Sparse canonical scatter produced zero measure.")
    normalization_factor = cic_masses.total_measure / raw_measure
    node_masses *= normalization_factor
    # One deterministic residual correction makes the stored mass sum match the
    # declared target to the accuracy of the chosen float64 summation order.
    corrected = float(np.sum(node_masses, dtype=np.float64))
    node_masses[0] += cic_masses.total_measure - corrected
    if node_masses[0] <= 0.0:
        raise GraphAdapterError("Sparse normalization produced a nonpositive node mass.")

    cell = stencil.display_cell
    voxel_volume = abs(float(np.linalg.det(cell))) / float(
        np.prod(shape, dtype=object)
    )
    active_values = node_masses / voxel_volume
    final_measure = float(np.sum(active_values, dtype=np.float64)) * voxel_volume
    return SparseCanonicalDensityReference3D(
        field_key=field_key,
        label=label,
        physical_units=physical_units,
        logical_grid_shape=shape,
        active_flat_indices=active_flat,
        active_values=active_values,
        display_cell=cell,
        total_measure=cic_masses.total_measure,
        gaussian_bandwidth=stencil.gaussian_bandwidth,
        broadening_metric=broadening_metric,
        source_provenance=cic_masses.source_provenance,
        metadata={
            "reference_path": "ld1_a_flat_sparse_nodes",
            "production_backend": False,
            "deposition_schema": cic_masses.schema_version,
            "stencil_schema": stencil.schema_version,
            "occupied_cic_node_count": occupied,
            "stencil_offset_count": stencil_count,
            "kernel_pair_count": pair_count,
            "active_node_count": int(active_flat.size),
            "raw_measure_before_final_normalization": raw_measure,
            "final_normalization_factor": normalization_factor,
            "final_measure": final_measure,
            "deterministic_accumulation_order": "stencil_major_then_source_stable",
            "workspace_upper_bound_bytes": workspace_upper,
            **stencil.metadata_dict(),
        },
    )


def prepare_sparse_canonical_density_reference(
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
    max_cic_contributions: int | None = None,
    max_stencil_candidate_contributions: int | None = None,
    max_kernel_pairs: int | None = None,
    max_workspace_bytes: int | None = None,
) -> SparseCanonicalDensityReference3D:
    """Prepare the complete LD1-A reference field from weighted samples."""

    budget, _model, derived = resolve_density_resource_limits()
    stencil_candidate_default = derived["max_density_stencil_values"]
    stencil_candidate_limit = (
        stencil_candidate_default
        if max_stencil_candidate_contributions is None
        else min(
            stencil_candidate_default,
            _positive_limit(
                max_stencil_candidate_contributions,
                name="max_stencil_candidate_contributions",
            ),
        )
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_limit(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    cic = aggregate_periodic_cic_sparse(
        samples,
        grid_shape,
        max_cic_contributions=max_cic_contributions,
        max_workspace_bytes=workspace_limit,
    )
    stencil = build_periodic_gaussian_stencil_support(
        grid_shape,
        display_cell,
        gaussian_bandwidth,
        kernel_tail_tolerance=kernel_tail_tolerance,
        max_candidate_contributions=stencil_candidate_limit,
        max_workspace_bytes=workspace_limit,
    )
    return scatter_periodic_stencil_sparse(
        cic,
        stencil,
        field_key=field_key,
        label=label,
        physical_units=physical_units,
        broadening_metric=broadening_metric,
        max_kernel_pairs=max_kernel_pairs,
        max_workspace_bytes=workspace_limit,
    )
