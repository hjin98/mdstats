"""Canonical periodic node-kernel construction and dense convolution.

The ``discrete_periodized_v1`` operator is a project-specific finite-support
periodized Gaussian stencil.  It is applied to node masses deposited by the
cloud-in-cell assignment of Hockney and Eastwood, *Computer Simulation Using
Particles* (1988).  FFT circular convolution, the isotropic Gaussian density,
and the chi-square radial law are standard mathematical background.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray
from scipy.fft import fftn, ifftn
from scipy.special import gammainccinv

from .density_contracts import (
    DISCRETE_PERIODIZED_OPERATOR,
    LEGACY_SPECTRAL_OPERATOR,
    DensityKernelOptions,
    FrozenJSONMapping,
    freeze_json_mapping,
)
from .graph_errors import GraphAdapterError, GraphComplexityError
from .runtime_resources import resolve_density_resource_limits
from .density_scheduler import current_density_worker_count
from .density_autotune import autotuned_fft_worker_count
from .density_gpu import (
    estimate_fft_cpu_seconds,
    try_gpu_circular_fft_convolution,
    try_gpu_spectral_filter,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

DENSITY_STENCIL_SCHEMA = "mdstats.periodic-gaussian-stencil.v1"
DENSITY_STENCIL_SUPPORT_SCHEMA = "mdstats.periodic-gaussian-stencil-support.v1"
DENSITY_STENCIL_MOMENTS_SCHEMA = "mdstats.periodic-gaussian-stencil-moments.v1"
MAX_STENCIL_CANDIDATE_CONTRIBUTIONS = 100_000_000
_STENCIL_CHUNK_SIZE = 262_144
_NEGATIVE_ROUNDOFF_FACTOR = 64.0


def _readonly_array(
    value: Any,
    dtype: Any,
    *,
    shape: tuple[int, ...] | None = None,
    name: str,
) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if shape is not None and array.shape != shape:
        raise GraphAdapterError(f"{name} must have shape {shape}; received {array.shape}.")
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError(f"{name} must contain only finite values.")
    array.setflags(write=False)
    return array


def _validated_shape(value: tuple[int, int, int] | Any) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphAdapterError("grid_shape must contain three entries.")
    result: list[int] = []
    for entry in value:
        if isinstance(entry, bool) or not isinstance(entry, (int, np.integer)):
            raise GraphAdapterError("grid_shape entries must be positive integers.")
        item = int(entry)
        if item <= 0:
            raise GraphAdapterError("grid_shape entries must be positive integers.")
        result.append(item)
    return tuple(result)  # type: ignore[return-value]


def _validated_cell(value: Any) -> FloatArray:
    cell = np.asarray(value, dtype=np.float64)
    if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
        raise GraphAdapterError("display_cell must be a finite 3x3 matrix.")
    determinant = float(np.linalg.det(cell))
    scale = max(1.0, float(np.linalg.norm(cell, ord=np.inf)) ** 3)
    if abs(determinant) <= 64.0 * np.finfo(np.float64).eps * scale:
        raise GraphAdapterError("display_cell must be nonsingular.")
    return np.array(cell, dtype=np.float64, copy=True, order="C")


@dataclass(frozen=True, slots=True)
class PeriodicGaussianStencil:
    """Immutable canonical discrete periodized Gaussian stencil."""

    grid_shape: tuple[int, int, int]
    display_cell: FloatArray
    gaussian_bandwidth: float
    kernel_tail_tolerance: float
    cutoff_radius: float
    values: FloatArray
    active_flat_indices: IntArray
    active_weights: FloatArray
    pre_normalization_sum: float
    normalization_factor: float
    periodic_image_contribution_count: int
    covariance: FloatArray
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_STENCIL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_STENCIL_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported Gaussian-stencil schema {self.schema_version!r}."
            )
        shape = _validated_shape(self.grid_shape)
        cell = _validated_cell(self.display_cell)
        sigma = float(self.gaussian_bandwidth)
        tolerance = float(self.kernel_tail_tolerance)
        cutoff = float(self.cutoff_radius)
        pre_sum = float(self.pre_normalization_sum)
        factor = float(self.normalization_factor)
        contribution_count = int(self.periodic_image_contribution_count)
        if not np.isfinite(sigma) or sigma < 0.0:
            raise GraphAdapterError("gaussian_bandwidth must be finite and nonnegative.")
        if not np.isfinite(tolerance) or not 1.0e-15 <= tolerance <= 1.0e-3:
            raise GraphAdapterError("kernel_tail_tolerance must lie in [1e-15, 1e-3].")
        if not np.isfinite(cutoff) or cutoff < 0.0:
            raise GraphAdapterError("cutoff_radius must be finite and nonnegative.")
        if not np.isfinite(pre_sum) or pre_sum <= 0.0:
            raise GraphAdapterError("pre_normalization_sum must be finite and positive.")
        if not np.isfinite(factor) or factor <= 0.0:
            raise GraphAdapterError("normalization_factor must be finite and positive.")
        if contribution_count <= 0:
            raise GraphAdapterError("periodic_image_contribution_count must be positive.")

        values = _readonly_array(self.values, np.float64, shape=shape, name="values")
        if np.any(values < 0.0):
            raise GraphAdapterError("Gaussian stencil values must be nonnegative.")
        indices = _readonly_array(
            self.active_flat_indices,
            np.int64,
            name="active_flat_indices",
        )
        weights = _readonly_array(
            self.active_weights,
            np.float64,
            name="active_weights",
        )
        if indices.ndim != 1 or weights.ndim != 1 or indices.shape != weights.shape:
            raise GraphAdapterError(
                "active_flat_indices and active_weights must be aligned vectors."
            )
        logical = int(np.prod(shape, dtype=object))
        if indices.size == 0 or int(indices[0]) < 0 or int(indices[-1]) >= logical:
            raise GraphAdapterError("Active stencil indices must lie in the logical grid.")
        if indices.size > 1 and np.any(indices[1:] <= indices[:-1]):
            raise GraphAdapterError("Active stencil indices must be strictly increasing.")
        flat = values.reshape(-1)
        if not np.array_equal(weights, flat[indices]):
            raise GraphAdapterError("Active stencil weights do not match the dense stencil.")
        if np.any(weights <= 0.0):
            raise GraphAdapterError("Active stencil weights must be positive.")
        total = float(np.sum(values, dtype=np.float64))
        if abs(total - 1.0) > 5.0e-15:
            raise GraphAdapterError(
                f"Gaussian stencil must sum to one; received {total:.17g}."
            )
        covariance = _readonly_array(
            self.covariance,
            np.float64,
            shape=(3, 3),
            name="covariance",
        )
        symmetry_error = float(np.max(np.abs(covariance - covariance.T)))
        if symmetry_error > 5.0e-13 * max(1.0, float(np.max(np.abs(covariance)))):
            raise GraphAdapterError("Gaussian stencil covariance must be symmetric.")

        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "gaussian_bandwidth", sigma)
        object.__setattr__(self, "kernel_tail_tolerance", tolerance)
        object.__setattr__(self, "cutoff_radius", cutoff)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "active_flat_indices", indices)
        object.__setattr__(self, "active_weights", weights)
        object.__setattr__(self, "pre_normalization_sum", pre_sum)
        object.__setattr__(self, "normalization_factor", factor)
        object.__setattr__(
            self, "periodic_image_contribution_count", contribution_count
        )
        object.__setattr__(self, "covariance", covariance)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def stencil_offset_count(self) -> int:
        return int(self.active_flat_indices.size)

    @property
    def voxel_volume(self) -> float:
        return abs(float(np.linalg.det(self.display_cell))) / float(
            np.prod(self.grid_shape, dtype=object)
        )

    def metadata_dict(self) -> dict[str, Any]:
        return {
            **self.metadata.to_json_dict(),
            "smoothing_operator": DISCRETE_PERIODIZED_OPERATOR,
            "kernel_tail_tolerance": self.kernel_tail_tolerance,
            "continuous_tail_mass_bound": (
                0.0 if self.gaussian_bandwidth == 0.0 else self.kernel_tail_tolerance
            ),
            "kernel_cutoff_radius": self.cutoff_radius,
            "stencil_pre_normalization_sum": self.pre_normalization_sum,
            "stencil_normalization_factor": self.normalization_factor,
            "stencil_offset_count": self.stencil_offset_count,
            "periodic_image_contribution_count": (
                self.periodic_image_contribution_count
            ),
            "stencil_covariance_cartesian": self.covariance.tolist(),
        }


@dataclass(frozen=True, slots=True)
class PeriodicGaussianStencilSupport:
    """Sparse-only canonical stencil support without a logical dense array."""

    grid_shape: tuple[int, int, int]
    display_cell: FloatArray
    gaussian_bandwidth: float
    kernel_tail_tolerance: float
    cutoff_radius: float
    active_flat_indices: IntArray
    active_weights: FloatArray
    pre_normalization_sum: float
    normalization_factor: float
    periodic_image_contribution_count: int
    covariance: FloatArray
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_STENCIL_SUPPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_STENCIL_SUPPORT_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported Gaussian-stencil-support schema {self.schema_version!r}."
            )
        shape = _validated_shape(self.grid_shape)
        cell = _validated_cell(self.display_cell)
        sigma = float(self.gaussian_bandwidth)
        tolerance = float(self.kernel_tail_tolerance)
        cutoff = float(self.cutoff_radius)
        pre_sum = float(self.pre_normalization_sum)
        factor = float(self.normalization_factor)
        contribution_count = int(self.periodic_image_contribution_count)
        if not np.isfinite(sigma) or sigma < 0.0:
            raise GraphAdapterError("gaussian_bandwidth must be finite and nonnegative.")
        if not np.isfinite(tolerance) or not 1.0e-15 <= tolerance <= 1.0e-3:
            raise GraphAdapterError("kernel_tail_tolerance must lie in [1e-15, 1e-3].")
        if not np.isfinite(cutoff) or cutoff < 0.0:
            raise GraphAdapterError("cutoff_radius must be finite and nonnegative.")
        if not np.isfinite(pre_sum) or pre_sum <= 0.0:
            raise GraphAdapterError("pre_normalization_sum must be finite and positive.")
        if not np.isfinite(factor) or factor <= 0.0:
            raise GraphAdapterError("normalization_factor must be finite and positive.")
        if contribution_count <= 0:
            raise GraphAdapterError("periodic_image_contribution_count must be positive.")
        indices = _readonly_array(
            self.active_flat_indices,
            np.int64,
            name="active_flat_indices",
        )
        weights = _readonly_array(
            self.active_weights,
            np.float64,
            name="active_weights",
        )
        if indices.ndim != 1 or weights.ndim != 1 or indices.shape != weights.shape:
            raise GraphAdapterError(
                "active_flat_indices and active_weights must be aligned vectors."
            )
        logical = int(np.prod(shape, dtype=object))
        if indices.size == 0 or int(indices[0]) < 0 or int(indices[-1]) >= logical:
            raise GraphAdapterError("Active stencil indices must lie in the logical grid.")
        if indices.size > 1 and np.any(indices[1:] <= indices[:-1]):
            raise GraphAdapterError("Active stencil indices must be strictly increasing.")
        if np.any(weights <= 0.0):
            raise GraphAdapterError("Active stencil weights must be positive.")
        total = float(np.sum(weights, dtype=np.float64))
        if abs(total - 1.0) > 5.0e-15:
            raise GraphAdapterError(
                f"Gaussian stencil support must sum to one; received {total:.17g}."
            )
        covariance = _readonly_array(
            self.covariance,
            np.float64,
            shape=(3, 3),
            name="covariance",
        )
        symmetry_error = float(np.max(np.abs(covariance - covariance.T)))
        if symmetry_error > 5.0e-13 * max(1.0, float(np.max(np.abs(covariance)))):
            raise GraphAdapterError("Gaussian stencil covariance must be symmetric.")
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "gaussian_bandwidth", sigma)
        object.__setattr__(self, "kernel_tail_tolerance", tolerance)
        object.__setattr__(self, "cutoff_radius", cutoff)
        object.__setattr__(self, "active_flat_indices", indices)
        object.__setattr__(self, "active_weights", weights)
        object.__setattr__(self, "pre_normalization_sum", pre_sum)
        object.__setattr__(self, "normalization_factor", factor)
        object.__setattr__(
            self, "periodic_image_contribution_count", contribution_count
        )
        object.__setattr__(self, "covariance", covariance)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def stencil_offset_count(self) -> int:
        return int(self.active_flat_indices.size)

    def to_dense_values(self, *, max_nodes: int | None = None) -> FloatArray:
        """Materialize the dense stencil only for a runtime-bounded debug case."""

        budget, _model, limits = resolve_density_resource_limits()
        default_limit = min(
            int(limits["max_density_stencil_values"]),
            max(1, budget.max_memory_bytes // (4 * np.dtype(np.float64).itemsize)),
        )
        if max_nodes is None:
            limit = default_limit
        else:
            if isinstance(max_nodes, bool) or not isinstance(max_nodes, (int, np.integer)):
                raise GraphAdapterError("max_nodes must be a positive integer or None.")
            limit = min(default_limit, int(max_nodes))
        if limit <= 0:
            raise GraphAdapterError("max_nodes must be positive.")
        logical = int(np.prod(self.grid_shape, dtype=object))
        if logical > limit:
            raise GraphComplexityError(
                f"Dense stencil conversion requires {logical} nodes, exceeding "
                f"max_nodes={limit}."
            )
        dense = np.zeros(logical, dtype=np.float64)
        dense[self.active_flat_indices] = self.active_weights
        dense = dense.reshape(self.grid_shape)
        dense.setflags(write=False)
        return dense

    def metadata_dict(self) -> dict[str, Any]:
        return {
            **self.metadata.to_json_dict(),
            "smoothing_operator": DISCRETE_PERIODIZED_OPERATOR,
            "kernel_tail_tolerance": self.kernel_tail_tolerance,
            "continuous_tail_mass_bound": (
                0.0 if self.gaussian_bandwidth == 0.0 else self.kernel_tail_tolerance
            ),
            "kernel_cutoff_radius": self.cutoff_radius,
            "stencil_pre_normalization_sum": self.pre_normalization_sum,
            "stencil_normalization_factor": self.normalization_factor,
            "stencil_offset_count": self.stencil_offset_count,
            "periodic_image_contribution_count": (
                self.periodic_image_contribution_count
            ),
            "stencil_covariance_cartesian": self.covariance.tolist(),
            "dense_stencil_allocated": False,
        }


@dataclass(frozen=True, slots=True)
class PeriodicGaussianStencilMoments:
    """Canonical-stencil moments without dense logical-grid allocation."""

    grid_shape: tuple[int, int, int]
    display_cell: FloatArray
    gaussian_bandwidth: float
    kernel_tail_tolerance: float
    cutoff_radius: float
    pre_normalization_sum: float
    normalization_factor: float
    periodic_image_contribution_count: int
    covariance: FloatArray
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_STENCIL_MOMENTS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_STENCIL_MOMENTS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported Gaussian-stencil-moments schema {self.schema_version!r}."
            )
        shape = _validated_shape(self.grid_shape)
        cell = _validated_cell(self.display_cell)
        sigma = float(self.gaussian_bandwidth)
        tolerance = float(self.kernel_tail_tolerance)
        cutoff = float(self.cutoff_radius)
        pre_sum = float(self.pre_normalization_sum)
        factor = float(self.normalization_factor)
        contribution_count = int(self.periodic_image_contribution_count)
        if not np.isfinite(sigma) or sigma < 0.0:
            raise GraphAdapterError("gaussian_bandwidth must be finite and nonnegative.")
        if not np.isfinite(tolerance) or not 1.0e-15 <= tolerance <= 1.0e-3:
            raise GraphAdapterError("kernel_tail_tolerance must lie in [1e-15, 1e-3].")
        if not np.isfinite(cutoff) or cutoff < 0.0:
            raise GraphAdapterError("cutoff_radius must be finite and nonnegative.")
        if not np.isfinite(pre_sum) or pre_sum <= 0.0:
            raise GraphAdapterError("pre_normalization_sum must be finite and positive.")
        if not np.isfinite(factor) or factor <= 0.0:
            raise GraphAdapterError("normalization_factor must be finite and positive.")
        if contribution_count <= 0:
            raise GraphAdapterError("periodic_image_contribution_count must be positive.")
        covariance = _readonly_array(
            self.covariance,
            np.float64,
            shape=(3, 3),
            name="covariance",
        )
        symmetry_error = float(np.max(np.abs(covariance - covariance.T)))
        if symmetry_error > 5.0e-13 * max(1.0, float(np.max(np.abs(covariance)))):
            raise GraphAdapterError("Gaussian stencil covariance must be symmetric.")
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "gaussian_bandwidth", sigma)
        object.__setattr__(self, "kernel_tail_tolerance", tolerance)
        object.__setattr__(self, "cutoff_radius", cutoff)
        object.__setattr__(self, "pre_normalization_sum", pre_sum)
        object.__setattr__(self, "normalization_factor", factor)
        object.__setattr__(
            self, "periodic_image_contribution_count", contribution_count
        )
        object.__setattr__(self, "covariance", covariance)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def metadata_dict(self) -> dict[str, Any]:
        return {
            **self.metadata.to_json_dict(),
            "smoothing_operator": DISCRETE_PERIODIZED_OPERATOR,
            "kernel_tail_tolerance": self.kernel_tail_tolerance,
            "continuous_tail_mass_bound": (
                0.0 if self.gaussian_bandwidth == 0.0 else self.kernel_tail_tolerance
            ),
            "kernel_cutoff_radius": self.cutoff_radius,
            "stencil_pre_normalization_sum": self.pre_normalization_sum,
            "stencil_normalization_factor": self.normalization_factor,
            "periodic_image_contribution_count": (
                self.periodic_image_contribution_count
            ),
            "stencil_covariance_cartesian": self.covariance.tolist(),
        }


def gaussian_cutoff_radius(
    gaussian_bandwidth: float,
    kernel_tail_tolerance: float,
) -> float:
    """Return the 3D isotropic-Gaussian radial cutoff."""

    sigma = float(gaussian_bandwidth)
    tolerance = float(kernel_tail_tolerance)
    if not np.isfinite(sigma) or sigma < 0.0:
        raise GraphAdapterError("gaussian_bandwidth must be finite and nonnegative.")
    if not np.isfinite(tolerance) or not 1.0e-15 <= tolerance <= 1.0e-3:
        raise GraphAdapterError("kernel_tail_tolerance must lie in [1e-15, 1e-3].")
    if sigma == 0.0:
        return 0.0
    quantile = 2.0 * float(gammainccinv(1.5, tolerance))
    if not np.isfinite(quantile) or quantile <= 0.0:
        raise GraphAdapterError("Failed to resolve the Gaussian radial cutoff.")
    return sigma * float(np.sqrt(quantile))


def _candidate_bounds(
    shape: tuple[int, int, int],
    cell: FloatArray,
    cutoff_radius: float,
) -> tuple[int, int, int]:
    inverse = np.linalg.inv(cell)
    fractional_bounds = cutoff_radius * np.linalg.norm(inverse, axis=0)
    raw = np.ceil(np.asarray(shape, dtype=np.float64) * fractional_bounds)
    if np.any(~np.isfinite(raw)) or np.any(raw > np.iinfo(np.int64).max // 4):
        raise GraphComplexityError("Gaussian stencil support bounds exceed integer range.")
    return tuple(int(value) for value in raw)  # type: ignore[return-value]



def build_periodic_gaussian_stencil_support(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    *,
    kernel_tail_tolerance: float = 1.0e-8,
    max_candidate_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
) -> PeriodicGaussianStencilSupport:
    """Build sparse canonical support without allocating the logical dense grid."""

    shape = _validated_shape(grid_shape)
    cell = _validated_cell(display_cell)
    sigma = float(gaussian_bandwidth)
    tolerance = float(kernel_tail_tolerance)
    cutoff = gaussian_cutoff_radius(sigma, tolerance)
    budget, _model, derived = resolve_density_resource_limits()
    default_candidate_limit = derived["max_density_stencil_values"]
    candidate_limit = (
        default_candidate_limit
        if max_candidate_contributions is None
        else min(
            default_candidate_limit,
            int(max_candidate_contributions),
        )
    )
    if candidate_limit <= 0:
        raise GraphAdapterError("max_candidate_contributions must be positive.")
    if max_workspace_bytes is None:
        workspace_limit = budget.max_memory_bytes
    else:
        if isinstance(max_workspace_bytes, bool) or not isinstance(
            max_workspace_bytes, (int, np.integer)
        ):
            raise GraphAdapterError("max_workspace_bytes must be a positive integer.")
        workspace_limit = min(int(max_workspace_bytes), budget.max_memory_bytes)
        if workspace_limit <= 0:
            raise GraphAdapterError("max_workspace_bytes must be positive.")
    if sigma == 0.0:
        return PeriodicGaussianStencilSupport(
            grid_shape=shape,
            display_cell=cell,
            gaussian_bandwidth=0.0,
            kernel_tail_tolerance=tolerance,
            cutoff_radius=0.0,
            active_flat_indices=np.asarray([0], dtype=np.int64),
            active_weights=np.asarray([1.0], dtype=np.float64),
            pre_normalization_sum=1.0,
            normalization_factor=1.0,
            periodic_image_contribution_count=1,
            covariance=np.zeros((3, 3), dtype=np.float64),
            metadata={
                "candidate_contribution_count": 1,
                "support_integer_bounds": [0, 0, 0],
                "workspace_upper_bound_bytes": 128,
            },
        )

    bounds = _candidate_bounds(shape, cell, cutoff)
    candidate_count = int(
        np.prod([2 * value + 1 for value in bounds], dtype=object)
    )
    if candidate_count > candidate_limit:
        raise GraphComplexityError(
            "Canonical Gaussian-stencil support requires "
            f"{candidate_count} candidate image contributions, exceeding "
            f"max_candidate_contributions={candidate_limit}."
        )
    # The sparse reference retains flat/value contribution vectors and stable-sort
    # work arrays.  This conservative bound is checked before enumeration.
    workspace_upper = 128 * candidate_count + 4096
    if workspace_upper > workspace_limit:
        raise GraphComplexityError(
            "Sparse Gaussian-stencil support requires at most "
            f"{workspace_upper} bytes of package-owned workspace, exceeding "
            f"max_workspace_bytes={workspace_limit}."
        )

    logical = int(np.prod(shape, dtype=object))
    voxel_volume = abs(float(np.linalg.det(cell))) / float(logical)
    gaussian_prefactor = voxel_volume / (
        (2.0 * np.pi * sigma * sigma) ** 1.5
    )
    cutoff2 = cutoff * cutoff
    radius_slack = 64.0 * np.finfo(np.float64).eps * max(1.0, cutoff2)
    covariance_numerator = np.zeros((3, 3), dtype=np.float64)
    pre_sum = 0.0
    retained_count = 0
    shape_array_float = np.asarray(shape, dtype=np.float64)
    shape_array_int = np.asarray(shape, dtype=np.int64)
    z_values = np.arange(-bounds[2], bounds[2] + 1, dtype=np.int64)
    chunk_point_budget = max(
        1,
        min(_STENCIL_CHUNK_SIZE, workspace_limit // 256),
    )
    y_chunk = max(1, chunk_point_budget // max(1, z_values.size))
    flat_parts: list[IntArray] = []
    weight_parts: list[FloatArray] = []

    for qx in range(-bounds[0], bounds[0] + 1):
        for y_start in range(-bounds[1], bounds[1] + 1, y_chunk):
            y_stop = min(bounds[1] + 1, y_start + y_chunk)
            y_values = np.arange(y_start, y_stop, dtype=np.int64)
            yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
            count = int(yy.size)
            q = np.empty((count, 3), dtype=np.int64)
            q[:, 0] = qx
            q[:, 1] = yy.reshape(-1)
            q[:, 2] = zz.reshape(-1)
            fractional = q.astype(np.float64) / shape_array_float[None, :]
            cartesian = fractional @ cell
            radius2 = np.einsum("ni,ni->n", cartesian, cartesian, optimize=True)
            mask = radius2 <= cutoff2 + radius_slack
            if not np.any(mask):
                continue
            retained_q = q[mask]
            retained_cartesian = cartesian[mask]
            retained_radius2 = radius2[mask]
            weights = gaussian_prefactor * np.exp(
                -0.5 * retained_radius2 / (sigma * sigma)
            )
            canonical = np.mod(retained_q, shape_array_int)
            flat = np.ravel_multi_index(
                (canonical[:, 0], canonical[:, 1], canonical[:, 2]),
                shape,
                order="C",
            ).astype(np.int64, copy=False)
            flat_parts.append(flat)
            weight_parts.append(weights)
            pre_sum += float(np.sum(weights, dtype=np.float64))
            covariance_numerator += np.einsum(
                "n,ni,nj->ij",
                weights,
                retained_cartesian,
                retained_cartesian,
                optimize=True,
            )
            retained_count += int(weights.size)

    if retained_count == 0 or not np.isfinite(pre_sum) or pre_sum <= 0.0:
        raise GraphAdapterError("Canonical Gaussian stencil has zero retained mass.")
    all_flat = np.concatenate(flat_parts).astype(np.int64, copy=False)
    all_weights = np.concatenate(weight_parts).astype(np.float64, copy=False)
    active_indices = np.unique(all_flat).astype(np.int64, copy=False)
    inverse = np.searchsorted(active_indices, all_flat)
    active_weights = np.zeros(active_indices.size, dtype=np.float64)
    # np.add.at preserves the image-enumeration order used by the dense builder.
    np.add.at(active_weights, inverse, all_weights)
    normalization_factor = 1.0 / pre_sum
    active_weights *= normalization_factor
    origin = int(np.searchsorted(active_indices, 0))
    if origin >= active_indices.size or int(active_indices[origin]) != 0:
        raise GraphAdapterError("Canonical Gaussian support does not contain the origin.")
    active_weights[origin] += 1.0 - float(np.sum(active_weights, dtype=np.float64))
    if active_weights[origin] <= 0.0:
        raise GraphAdapterError("Stencil normalization produced a nonpositive origin.")
    covariance = covariance_numerator * normalization_factor
    covariance = 0.5 * (covariance + covariance.T)
    return PeriodicGaussianStencilSupport(
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        kernel_tail_tolerance=tolerance,
        cutoff_radius=cutoff,
        active_flat_indices=active_indices,
        active_weights=active_weights,
        pre_normalization_sum=pre_sum,
        normalization_factor=normalization_factor,
        periodic_image_contribution_count=retained_count,
        covariance=covariance,
        metadata={
            "candidate_contribution_count": candidate_count,
            "support_integer_bounds": list(bounds),
            "workspace_upper_bound_bytes": workspace_upper,
        },
    )

def build_periodic_gaussian_stencil(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    *,
    kernel_tail_tolerance: float = 1.0e-8,
    max_candidate_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
) -> PeriodicGaussianStencil:
    """Build ``discrete_periodized_v1`` in deterministic lexicographic order."""

    shape = _validated_shape(grid_shape)
    cell = _validated_cell(display_cell)
    sigma = float(gaussian_bandwidth)
    tolerance = float(kernel_tail_tolerance)
    cutoff = gaussian_cutoff_radius(sigma, tolerance)
    logical = int(np.prod(shape, dtype=object))
    budget, _model, derived = resolve_density_resource_limits()
    default_candidate_limit = derived["max_density_stencil_values"]
    candidate_limit = (
        default_candidate_limit
        if max_candidate_contributions is None
        else min(
            default_candidate_limit,
            int(max_candidate_contributions),
        )
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(int(max_workspace_bytes), budget.max_memory_bytes)
    )
    if candidate_limit <= 0 or workspace_limit <= 0:
        raise GraphAdapterError("Dense stencil limits must be positive.")
    if logical * 8 > workspace_limit:
        raise GraphComplexityError(
            f"Dense Gaussian stencil requires at least {logical * 8} bytes, "
            f"exceeding max_workspace_bytes={workspace_limit}."
        )
    if sigma == 0.0:
        values = np.zeros(shape, dtype=np.float64)
        values[0, 0, 0] = 1.0
        return PeriodicGaussianStencil(
            grid_shape=shape,
            display_cell=cell,
            gaussian_bandwidth=0.0,
            kernel_tail_tolerance=tolerance,
            cutoff_radius=0.0,
            values=values,
            active_flat_indices=np.asarray([0], dtype=np.int64),
            active_weights=np.asarray([1.0], dtype=np.float64),
            pre_normalization_sum=1.0,
            normalization_factor=1.0,
            periodic_image_contribution_count=1,
            covariance=np.zeros((3, 3), dtype=np.float64),
            metadata={
                "candidate_contribution_count": 1,
                "support_integer_bounds": [0, 0, 0],
            },
        )

    bounds = _candidate_bounds(shape, cell, cutoff)
    candidate_count = int(
        np.prod([2 * value + 1 for value in bounds], dtype=object)
    )
    if candidate_count > candidate_limit:
        raise GraphComplexityError(
            "Canonical Gaussian-stencil support requires "
            f"{candidate_count} candidate image contributions, exceeding "
            f"max_candidate_contributions={candidate_limit}."
        )

    dense_workspace_upper = logical * 8 + 128 * candidate_count + 4096
    if dense_workspace_upper > workspace_limit:
        raise GraphComplexityError(
            f"Dense Gaussian stencil requires at most {dense_workspace_upper} bytes, "
            f"exceeding max_workspace_bytes={workspace_limit}."
        )
    voxel_volume = abs(float(np.linalg.det(cell))) / float(logical)
    gaussian_prefactor = voxel_volume / (
        (2.0 * np.pi * sigma * sigma) ** 1.5
    )
    cutoff2 = cutoff * cutoff
    radius_slack = 64.0 * np.finfo(np.float64).eps * max(1.0, cutoff2)
    dense = np.zeros(logical, dtype=np.float64)
    covariance_numerator = np.zeros((3, 3), dtype=np.float64)
    pre_sum = 0.0
    retained_count = 0
    shape_array = np.asarray(shape, dtype=np.float64)
    z_values = np.arange(-bounds[2], bounds[2] + 1, dtype=np.int64)
    chunk_point_budget = max(
        1,
        min(_STENCIL_CHUNK_SIZE, workspace_limit // 256),
    )
    y_chunk = max(1, chunk_point_budget // max(1, z_values.size))

    for qx in range(-bounds[0], bounds[0] + 1):
        for y_start in range(-bounds[1], bounds[1] + 1, y_chunk):
            y_stop = min(bounds[1] + 1, y_start + y_chunk)
            y_values = np.arange(y_start, y_stop, dtype=np.int64)
            yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
            count = int(yy.size)
            q = np.empty((count, 3), dtype=np.int64)
            q[:, 0] = qx
            q[:, 1] = yy.reshape(-1)
            q[:, 2] = zz.reshape(-1)
            fractional = q.astype(np.float64) / shape_array[None, :]
            cartesian = fractional @ cell
            radius2 = np.einsum(
                "ni,ni->n", cartesian, cartesian, optimize=True
            )
            mask = radius2 <= cutoff2 + radius_slack
            if not np.any(mask):
                continue
            retained_q = q[mask]
            retained_cartesian = cartesian[mask]
            retained_radius2 = radius2[mask]
            weights = gaussian_prefactor * np.exp(
                -0.5 * retained_radius2 / (sigma * sigma)
            )
            canonical = np.mod(retained_q, np.asarray(shape, dtype=np.int64))
            flat = np.ravel_multi_index(
                (canonical[:, 0], canonical[:, 1], canonical[:, 2]),
                shape,
                order="C",
            )
            np.add.at(dense, flat, weights)
            pre_sum += float(np.sum(weights, dtype=np.float64))
            covariance_numerator += np.einsum(
                "n,ni,nj->ij",
                weights,
                retained_cartesian,
                retained_cartesian,
                optimize=True,
            )
            retained_count += int(weights.size)

    if retained_count == 0 or not np.isfinite(pre_sum) or pre_sum <= 0.0:
        raise GraphAdapterError("Canonical Gaussian stencil has zero retained mass.")
    normalization_factor = 1.0 / pre_sum
    dense *= normalization_factor
    normalized_sum = float(np.sum(dense, dtype=np.float64))
    dense[0] += 1.0 - normalized_sum
    if dense[0] <= 0.0:
        raise GraphAdapterError("Stencil normalization produced a nonpositive origin.")
    active_indices = np.flatnonzero(dense > 0.0).astype(np.int64, copy=False)
    covariance = covariance_numerator * normalization_factor
    covariance = 0.5 * (covariance + covariance.T)

    return PeriodicGaussianStencil(
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        kernel_tail_tolerance=tolerance,
        cutoff_radius=cutoff,
        values=dense.reshape(shape),
        active_flat_indices=active_indices,
        active_weights=dense[active_indices],
        pre_normalization_sum=pre_sum,
        normalization_factor=normalization_factor,
        periodic_image_contribution_count=retained_count,
        covariance=covariance,
        metadata={
            "candidate_contribution_count": candidate_count,
            "support_integer_bounds": list(bounds),
        },
    )



def periodic_gaussian_stencil_moments(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    *,
    kernel_tail_tolerance: float = 1.0e-8,
    max_candidate_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
) -> PeriodicGaussianStencilMoments:
    """Return canonical-stencil covariance without allocating dense stencil values."""

    shape = _validated_shape(grid_shape)
    cell = _validated_cell(display_cell)
    sigma = float(gaussian_bandwidth)
    tolerance = float(kernel_tail_tolerance)
    cutoff = gaussian_cutoff_radius(sigma, tolerance)
    budget, _model, derived = resolve_density_resource_limits()
    default_candidate_limit = derived["max_density_stencil_values"]
    candidate_limit = (
        default_candidate_limit
        if max_candidate_contributions is None
        else min(
            default_candidate_limit,
            int(max_candidate_contributions),
        )
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(int(max_workspace_bytes), budget.max_memory_bytes)
    )
    if candidate_limit <= 0 or workspace_limit <= 0:
        raise GraphAdapterError("Stencil-moment limits must be positive.")
    if sigma == 0.0:
        return PeriodicGaussianStencilMoments(
            grid_shape=shape,
            display_cell=cell,
            gaussian_bandwidth=0.0,
            kernel_tail_tolerance=tolerance,
            cutoff_radius=0.0,
            pre_normalization_sum=1.0,
            normalization_factor=1.0,
            periodic_image_contribution_count=1,
            covariance=np.zeros((3, 3), dtype=np.float64),
            metadata={
                "candidate_contribution_count": 1,
                "support_integer_bounds": [0, 0, 0],
                "dense_stencil_allocated": False,
            },
        )

    bounds = _candidate_bounds(shape, cell, cutoff)
    candidate_count = int(
        np.prod([2 * value + 1 for value in bounds], dtype=object)
    )
    if candidate_count > candidate_limit:
        raise GraphComplexityError(
            "Canonical Gaussian-stencil support requires "
            f"{candidate_count} candidate image contributions, exceeding "
            f"max_candidate_contributions={candidate_limit}."
        )

    workspace_upper = 96 * candidate_count + 4096
    if workspace_upper > workspace_limit:
        raise GraphComplexityError(
            f"Gaussian stencil moments require at most {workspace_upper} bytes, "
            f"exceeding max_workspace_bytes={workspace_limit}."
        )
    logical = int(np.prod(shape, dtype=object))
    voxel_volume = abs(float(np.linalg.det(cell))) / float(logical)
    gaussian_prefactor = voxel_volume / (
        (2.0 * np.pi * sigma * sigma) ** 1.5
    )
    cutoff2 = cutoff * cutoff
    radius_slack = 64.0 * np.finfo(np.float64).eps * max(1.0, cutoff2)
    covariance_numerator = np.zeros((3, 3), dtype=np.float64)
    pre_sum = 0.0
    retained_count = 0
    shape_array = np.asarray(shape, dtype=np.float64)
    z_values = np.arange(-bounds[2], bounds[2] + 1, dtype=np.int64)
    chunk_point_budget = max(
        1,
        min(_STENCIL_CHUNK_SIZE, workspace_limit // 256),
    )
    y_chunk = max(1, chunk_point_budget // max(1, z_values.size))

    for qx in range(-bounds[0], bounds[0] + 1):
        for y_start in range(-bounds[1], bounds[1] + 1, y_chunk):
            y_stop = min(bounds[1] + 1, y_start + y_chunk)
            y_values = np.arange(y_start, y_stop, dtype=np.int64)
            yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
            count = int(yy.size)
            q = np.empty((count, 3), dtype=np.int64)
            q[:, 0] = qx
            q[:, 1] = yy.reshape(-1)
            q[:, 2] = zz.reshape(-1)
            fractional = q.astype(np.float64) / shape_array[None, :]
            cartesian = fractional @ cell
            radius2 = np.einsum(
                "ni,ni->n", cartesian, cartesian, optimize=True
            )
            mask = radius2 <= cutoff2 + radius_slack
            if not np.any(mask):
                continue
            retained_cartesian = cartesian[mask]
            retained_radius2 = radius2[mask]
            weights = gaussian_prefactor * np.exp(
                -0.5 * retained_radius2 / (sigma * sigma)
            )
            pre_sum += float(np.sum(weights, dtype=np.float64))
            covariance_numerator += np.einsum(
                "n,ni,nj->ij",
                weights,
                retained_cartesian,
                retained_cartesian,
                optimize=True,
            )
            retained_count += int(weights.size)

    if retained_count == 0 or not np.isfinite(pre_sum) or pre_sum <= 0.0:
        raise GraphAdapterError("Canonical Gaussian stencil has zero retained mass.")
    normalization_factor = 1.0 / pre_sum
    covariance = covariance_numerator * normalization_factor
    covariance = 0.5 * (covariance + covariance.T)
    return PeriodicGaussianStencilMoments(
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        kernel_tail_tolerance=tolerance,
        cutoff_radius=cutoff,
        pre_normalization_sum=pre_sum,
        normalization_factor=normalization_factor,
        periodic_image_contribution_count=retained_count,
        covariance=covariance,
        metadata={
            "candidate_contribution_count": candidate_count,
            "support_integer_bounds": list(bounds),
            "dense_stencil_allocated": False,
        },
    )


def _validated_mass_grid(mass_grid: Any, shape: tuple[int, int, int]) -> FloatArray:
    mass = np.asarray(mass_grid, dtype=np.float64)
    if mass.shape != shape or np.any(~np.isfinite(mass)):
        raise GraphAdapterError(
            f"mass_grid must be a finite array with shape {shape}."
        )
    tolerance = 64.0 * np.finfo(np.float64).eps * max(
        1.0, float(np.max(np.abs(mass)))
    )
    if float(np.min(mass)) < -tolerance:
        raise GraphAdapterError("mass_grid contains negative mass beyond roundoff.")
    result = np.array(mass, dtype=np.float64, copy=True, order="C")
    result[result < 0.0] = 0.0
    return result


def _complete_canonical_convolution(
    values: FloatArray,
    *,
    original_mass: float,
) -> tuple[FloatArray, int, float]:
    result = np.array(values, dtype=np.float64, copy=True, order="C")
    scale = max(1.0, float(np.max(np.abs(result))))
    negative_tolerance = (
        _NEGATIVE_ROUNDOFF_FACTOR * np.finfo(np.float64).eps * scale
    )
    minimum = float(np.min(result))
    if minimum < -negative_tolerance:
        raise GraphAdapterError(
            "Canonical FFT convolution produced negativity beyond roundoff: "
            f"minimum={minimum:.17g}, tolerance={negative_tolerance:.17g}."
        )
    negative = result < 0.0
    negative_count = int(np.count_nonzero(negative))
    result[negative] = 0.0
    if original_mass == 0.0:
        result.fill(0.0)
        return result, negative_count, 1.0
    current = float(np.sum(result, dtype=np.float64))
    if not np.isfinite(current) or current <= 0.0:
        raise GraphAdapterError("Canonical convolution destroyed mass normalization.")
    factor = original_mass / current
    result *= factor
    return result, negative_count, factor


def convolve_periodic_stencil_direct(
    mass_grid: FloatArray,
    stencil: PeriodicGaussianStencil,
) -> FloatArray:
    """Apply the canonical stencil by deterministic direct circular convolution."""

    mass = _validated_mass_grid(mass_grid, stencil.grid_shape)
    if stencil.gaussian_bandwidth == 0.0:
        return mass
    result = np.zeros(stencil.grid_shape, dtype=np.float64)
    for flat_index, weight in zip(
        stencil.active_flat_indices,
        stencil.active_weights,
        strict=True,
    ):
        offset = np.unravel_index(int(flat_index), stencil.grid_shape, order="C")
        result += float(weight) * np.roll(mass, shift=offset, axis=(0, 1, 2))
    completed, _, _ = _complete_canonical_convolution(
        result,
        original_mass=float(np.sum(mass, dtype=np.float64)),
    )
    return completed


def convolve_periodic_stencil_fft(
    mass_grid: FloatArray,
    stencil: PeriodicGaussianStencil,
) -> FloatArray:
    """Apply the canonical stencil by dense FFT circular convolution."""

    mass = _validated_mass_grid(mass_grid, stencil.grid_shape)
    if stencil.gaussian_bandwidth == 0.0:
        return mass
    workers = autotuned_fft_worker_count(current_density_worker_count(default=1))
    _budget, time_model, _derived = resolve_density_resource_limits()
    cpu_estimate = estimate_fft_cpu_seconds(
        int(mass.size), work_units_per_second=time_model.fft_work_units_per_second
    )
    raw = try_gpu_circular_fft_convolution(
        mass,
        stencil.values,
        cpu_estimate_seconds=cpu_estimate,
        kernel_name="dense_periodic_stencil_fft",
    )
    if raw is None:
        raw = ifftn(
            fftn(mass, workers=workers) * fftn(stencil.values, workers=workers),
            workers=workers,
        ).real
    completed, _, _ = _complete_canonical_convolution(
        raw,
        original_mass=float(np.sum(mass, dtype=np.float64)),
    )
    return completed


def _legacy_spectral_gaussian(
    mass_grid: FloatArray,
    cell: FloatArray,
    sigma: float,
) -> tuple[FloatArray, FrozenJSONMapping]:
    """Historical finite-mode spectral Gaussian, preserved byte-for-byte."""

    mass = np.asarray(mass_grid, dtype=np.float64)
    if sigma == 0.0:
        return np.array(mass, copy=True), freeze_json_mapping(
            {
                "smoothing_operator": LEGACY_SPECTRAL_OPERATOR,
                "legacy_positive_tail_clipping": False,
                "legacy_post_convolution_normalization_factor": 1.0,
            }
        )
    modes = [np.fft.fftfreq(n, d=1.0 / n) for n in mass.shape]
    mx, my, mz = np.meshgrid(*modes, indexing="ij")
    integer_modes = np.stack((mx, my, mz), axis=-1)
    reciprocal = 2.0 * np.pi * (integer_modes @ np.linalg.inv(cell).T)
    k2 = np.einsum("...i,...i->...", reciprocal, reciprocal, optimize=True)
    kernel = np.exp(-0.5 * sigma * sigma * k2)
    workers = autotuned_fft_worker_count(current_density_worker_count(default=1))
    _budget, time_model, _derived = resolve_density_resource_limits()
    cpu_estimate = estimate_fft_cpu_seconds(
        int(mass.size), work_units_per_second=time_model.fft_work_units_per_second
    )
    smoothed = try_gpu_spectral_filter(
        mass,
        kernel,
        cpu_estimate_seconds=cpu_estimate,
        kernel_name="dense_legacy_spectral_gaussian",
    )
    execution_backend = "torch_cuda_fp64" if smoothed is not None else "scipy_fft_cpu"
    if smoothed is None:
        smoothed = ifftn(fftn(mass, workers=workers) * kernel, workers=workers).real
    threshold = 1.0e-13 * max(1.0, float(np.max(np.abs(smoothed))))
    clipped_count = int(np.count_nonzero(smoothed < threshold))
    smoothed[smoothed < threshold] = 0.0
    original = float(np.sum(mass))
    current = float(np.sum(smoothed))
    if current <= 0.0:
        raise GraphAdapterError("Gaussian smoothing destroyed the density normalization.")
    factor = original / current
    smoothed *= factor
    return smoothed, freeze_json_mapping(
        {
            "smoothing_operator": LEGACY_SPECTRAL_OPERATOR,
            "legacy_clipping_threshold": threshold,
            "legacy_clipped_value_count": clipped_count,
            "legacy_positive_tail_clipping": True,
            "legacy_post_convolution_normalization_factor": factor,
            "fft_execution_backend": execution_backend,
            "gpu_execution_is_scientifically_neutral": True,
        }
    )


def smooth_periodic_node_masses(
    mass_grid: FloatArray,
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    kernel_options: DensityKernelOptions,
) -> tuple[FloatArray, FrozenJSONMapping]:
    """Dispatch one declared dense smoothing operator and return diagnostics."""

    cell = _validated_cell(display_cell)
    sigma = float(gaussian_bandwidth)
    if kernel_options.smoothing_operator == LEGACY_SPECTRAL_OPERATOR:
        return _legacy_spectral_gaussian(mass_grid, cell, sigma)
    if kernel_options.smoothing_operator != DISCRETE_PERIODIZED_OPERATOR:
        raise GraphAdapterError(
            f"Unsupported smoothing operator {kernel_options.smoothing_operator!r}."
        )
    mass = _validated_mass_grid(mass_grid, tuple(np.asarray(mass_grid).shape))
    if mass.ndim != 3:
        raise GraphAdapterError("mass_grid must be three-dimensional.")
    if sigma == 0.0:
        return np.array(mass, copy=True), freeze_json_mapping(
            {
                "smoothing_operator": DISCRETE_PERIODIZED_OPERATOR,
                "kernel_tail_tolerance": kernel_options.kernel_tail_tolerance,
                "continuous_tail_mass_bound": 0.0,
                "kernel_cutoff_radius": 0.0,
                "stencil_pre_normalization_sum": 1.0,
                "stencil_normalization_factor": 1.0,
                "stencil_offset_count": 1,
                "periodic_image_contribution_count": 1,
                "stencil_covariance_cartesian": [
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0],
                ],
                "canonical_convolution_method": "identity",
                "canonical_negative_roundoff_clipped": 0,
                "canonical_post_convolution_normalization_factor": 1.0,
            }
        )
    stencil = build_periodic_gaussian_stencil(
        mass.shape,
        cell,
        sigma,
        kernel_tail_tolerance=kernel_options.kernel_tail_tolerance,
    )
    workers = autotuned_fft_worker_count(current_density_worker_count(default=1))
    _budget, time_model, _derived = resolve_density_resource_limits()
    cpu_estimate = estimate_fft_cpu_seconds(
        int(mass.size), work_units_per_second=time_model.fft_work_units_per_second
    )
    raw = try_gpu_circular_fft_convolution(
        mass,
        stencil.values,
        cpu_estimate_seconds=cpu_estimate,
        kernel_name="dense_discrete_periodized_gaussian",
    )
    execution_backend = "torch_cuda_fp64" if raw is not None else "scipy_fft_cpu"
    if raw is None:
        raw = ifftn(
            fftn(mass, workers=workers) * fftn(stencil.values, workers=workers),
            workers=workers,
        ).real
    smoothed, negative_count, factor = _complete_canonical_convolution(
        raw,
        original_mass=float(np.sum(mass, dtype=np.float64)),
    )
    diagnostics = {
        **stencil.metadata_dict(),
        "canonical_convolution_method": "fft",
        "canonical_negative_roundoff_clipped": negative_count,
        "canonical_post_convolution_normalization_factor": factor,
        "fft_execution_backend": execution_backend,
        "gpu_execution_is_scientifically_neutral": True,
    }
    return smoothed, freeze_json_mapping(diagnostics)

# Stage 11E-GR0 compatibility ownership: stencil moments are analysis-owned.
from ..analysis.density.numerical_errors import (
    DensityNumericalInputError as _DensityNumericalInputError,
    DensityNumericalResourceError as _DensityNumericalResourceError,
)
from ..analysis.density.stencil_diagnostics import (
    PeriodicGaussianStencilMoments as PeriodicGaussianStencilMoments,
    periodic_gaussian_stencil_moments as _analysis_periodic_gaussian_stencil_moments,
)


def periodic_gaussian_stencil_moments(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    *,
    kernel_tail_tolerance: float = 1.0e-8,
    max_candidate_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
) -> PeriodicGaussianStencilMoments:
    """Plotting adapter for the analysis-owned GR0 stencil diagnostic."""

    budget, _model, derived = resolve_density_resource_limits()
    candidate_limit = (
        int(derived["max_density_stencil_values"])
        if max_candidate_contributions is None
        else min(
            int(derived["max_density_stencil_values"]),
            int(max_candidate_contributions),
        )
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(int(max_workspace_bytes), budget.max_memory_bytes)
    )
    try:
        return _analysis_periodic_gaussian_stencil_moments(
            grid_shape,
            display_cell,
            gaussian_bandwidth,
            kernel_tail_tolerance=kernel_tail_tolerance,
            max_candidate_contributions=candidate_limit,
            max_workspace_bytes=workspace_limit,
        )
    except _DensityNumericalResourceError as error:
        raise GraphComplexityError(str(error)) from error
    except _DensityNumericalInputError as error:
        raise GraphAdapterError(str(error)) from error

from ..analysis.density.stencil_diagnostics import (
    gaussian_cutoff_radius as _analysis_gaussian_cutoff_radius,
)


def gaussian_cutoff_radius(
    gaussian_bandwidth: float,
    kernel_tail_tolerance: float,
) -> float:
    """Plotting adapter for the analysis-owned Gaussian cutoff diagnostic."""

    try:
        return _analysis_gaussian_cutoff_radius(
            gaussian_bandwidth, kernel_tail_tolerance
        )
    except _DensityNumericalResourceError as error:
        raise GraphComplexityError(str(error)) from error
    except _DensityNumericalInputError as error:
        raise GraphAdapterError(str(error)) from error
