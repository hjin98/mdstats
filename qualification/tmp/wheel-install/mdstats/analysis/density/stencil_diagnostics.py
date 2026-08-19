"""Analysis-owned canonical Gaussian-stencil moment diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray
from scipy.special import gammainccinv

from ._frozen_json import FrozenJSONMapping, freeze_json_mapping
from .numerical_errors import DensityNumericalInputError, DensityNumericalResourceError

FloatArray = NDArray[np.float64]
DENSITY_STENCIL_MOMENTS_SCHEMA = "mdstats.periodic-gaussian-stencil-moments.v1"
DISCRETE_PERIODIZED_OPERATOR = "discrete_periodized_v1"
MAX_STENCIL_CANDIDATE_CONTRIBUTIONS = 100_000_000
DEFAULT_STENCIL_WORKSPACE_BYTES = 8 * 1024**3
_STENCIL_CHUNK_SIZE = 262_144


def _readonly_array(
    value: Any,
    dtype: Any,
    *,
    shape: tuple[int, ...] | None = None,
    name: str,
) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if shape is not None and array.shape != shape:
        raise DensityNumericalInputError(
            f"{name} must have shape {shape}; received {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise DensityNumericalInputError(f"{name} must contain only finite values.")
    array.setflags(write=False)
    return array


def _validated_shape(value: tuple[int, int, int] | Any) -> tuple[int, int, int]:
    try:
        entries = tuple(value)
    except TypeError as error:
        raise DensityNumericalInputError(
            "grid_shape must contain three entries."
        ) from error
    if len(entries) != 3:
        raise DensityNumericalInputError("grid_shape must contain three entries.")
    result: list[int] = []
    for entry in entries:
        if isinstance(entry, bool) or not isinstance(entry, (int, np.integer)):
            raise DensityNumericalInputError(
                "grid_shape entries must be positive integers."
            )
        item = int(entry)
        if item <= 0:
            raise DensityNumericalInputError(
                "grid_shape entries must be positive integers."
            )
        result.append(item)
    return tuple(result)  # type: ignore[return-value]


def _validated_cell(value: Any) -> FloatArray:
    cell = np.asarray(value, dtype=np.float64)
    if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
        raise DensityNumericalInputError("display_cell must be a finite 3x3 matrix.")
    determinant = float(np.linalg.det(cell))
    scale = max(1.0, float(np.linalg.norm(cell, ord=np.inf)) ** 3)
    if abs(determinant) <= 64.0 * np.finfo(np.float64).eps * scale:
        raise DensityNumericalInputError("display_cell must be nonsingular.")
    return np.array(cell, dtype=np.float64, copy=True, order="C")


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
            raise DensityNumericalInputError(
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
            raise DensityNumericalInputError(
                "gaussian_bandwidth must be finite and nonnegative."
            )
        if not np.isfinite(tolerance) or not 1.0e-15 <= tolerance <= 1.0e-3:
            raise DensityNumericalInputError(
                "kernel_tail_tolerance must lie in [1e-15, 1e-3]."
            )
        if not np.isfinite(cutoff) or cutoff < 0.0:
            raise DensityNumericalInputError(
                "cutoff_radius must be finite and nonnegative."
            )
        if not np.isfinite(pre_sum) or pre_sum <= 0.0:
            raise DensityNumericalInputError(
                "pre_normalization_sum must be finite and positive."
            )
        if not np.isfinite(factor) or factor <= 0.0:
            raise DensityNumericalInputError(
                "normalization_factor must be finite and positive."
            )
        if contribution_count <= 0:
            raise DensityNumericalInputError(
                "periodic_image_contribution_count must be positive."
            )
        covariance = _readonly_array(
            self.covariance, np.float64, shape=(3, 3), name="covariance"
        )
        symmetry_error = float(np.max(np.abs(covariance - covariance.T)))
        if symmetry_error > 5.0e-13 * max(
            1.0, float(np.max(np.abs(covariance)))
        ):
            raise DensityNumericalInputError(
                "Gaussian stencil covariance must be symmetric."
            )
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
                0.0
                if self.gaussian_bandwidth == 0.0
                else self.kernel_tail_tolerance
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
        raise DensityNumericalInputError(
            "gaussian_bandwidth must be finite and nonnegative."
        )
    if not np.isfinite(tolerance) or not 1.0e-15 <= tolerance <= 1.0e-3:
        raise DensityNumericalInputError(
            "kernel_tail_tolerance must lie in [1e-15, 1e-3]."
        )
    if sigma == 0.0:
        return 0.0
    quantile = 2.0 * float(gammainccinv(1.5, tolerance))
    if not np.isfinite(quantile) or quantile <= 0.0:
        raise DensityNumericalInputError(
            "Failed to resolve the Gaussian radial cutoff."
        )
    return sigma * float(np.sqrt(quantile))


def _candidate_bounds(
    shape: tuple[int, int, int],
    cell: FloatArray,
    cutoff_radius: float,
) -> tuple[int, int, int]:
    inverse = np.linalg.inv(cell)
    fractional_bounds = cutoff_radius * np.linalg.norm(inverse, axis=0)
    raw = np.ceil(np.asarray(shape, dtype=np.float64) * fractional_bounds)
    if np.any(~np.isfinite(raw)) or np.any(
        raw > np.iinfo(np.int64).max // 4
    ):
        raise DensityNumericalResourceError(
            "Gaussian stencil support bounds exceed integer range."
        )
    return tuple(int(value) for value in raw)  # type: ignore[return-value]


def periodic_gaussian_stencil_moments(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    *,
    kernel_tail_tolerance: float = 1.0e-8,
    max_candidate_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
) -> PeriodicGaussianStencilMoments:
    """Return canonical-stencil covariance without dense stencil allocation."""

    shape = _validated_shape(grid_shape)
    cell = _validated_cell(display_cell)
    sigma = float(gaussian_bandwidth)
    tolerance = float(kernel_tail_tolerance)
    cutoff = gaussian_cutoff_radius(sigma, tolerance)
    candidate_limit = (
        MAX_STENCIL_CANDIDATE_CONTRIBUTIONS
        if max_candidate_contributions is None
        else int(max_candidate_contributions)
    )
    workspace_limit = (
        DEFAULT_STENCIL_WORKSPACE_BYTES
        if max_workspace_bytes is None
        else int(max_workspace_bytes)
    )
    if candidate_limit <= 0 or workspace_limit <= 0:
        raise DensityNumericalInputError(
            "Stencil-moment limits must be positive."
        )
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
        raise DensityNumericalResourceError(
            "Canonical Gaussian-stencil support requires "
            f"{candidate_count} candidate image contributions, exceeding "
            f"max_candidate_contributions={candidate_limit}."
        )

    workspace_upper = 96 * candidate_count + 4096
    if workspace_upper > workspace_limit:
        raise DensityNumericalResourceError(
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
        raise DensityNumericalInputError(
            "Canonical Gaussian stencil has zero retained mass."
        )
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
