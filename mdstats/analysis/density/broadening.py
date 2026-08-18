"""Analysis-owned artificial broadening for periodic CIC plus smoothing.

The cloud-in-cell assignment follows Hockney and Eastwood, *Computer
Simulation Using Particles* (1988). Covariance addition for centered kernels is
standard probability theory. The phase-resolved periodic covariance and its
versioned use in adaptive density resolution are project-specific.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from numpy.typing import NDArray

from ._frozen_json import FrozenJSONMapping, freeze_json_mapping
from .stencil_diagnostics import (
    MAX_STENCIL_CANDIDATE_CONTRIBUTIONS,
    PeriodicGaussianStencilMoments,
    periodic_gaussian_stencil_moments,
)
from .numerical_errors import DensityNumericalInputError

FloatArray = NDArray[np.float64]

EFFECTIVE_CIC_STENCIL_BROADENING = "effective_cic_stencil_rms_v1"

DENSITY_BROADENING_SCHEMA = "mdstats.artificial-broadening-diagnostic.v1"


def _readonly_array(
    value: Any,
    *,
    shape: tuple[int, ...],
    name: str,
) -> FloatArray:
    array = np.array(value, dtype=np.float64, copy=True, order="C")
    if array.shape != shape or np.any(~np.isfinite(array)):
        raise DensityNumericalInputError(f"{name} must be a finite array with shape {shape}.")
    array.setflags(write=False)
    return array


def _validated_shape(value: tuple[int, int, int] | Any) -> tuple[int, int, int]:
    if len(value) != 3:
        raise DensityNumericalInputError("grid_shape must contain three entries.")
    result: list[int] = []
    for entry in value:
        if isinstance(entry, bool) or not isinstance(entry, (int, np.integer)):
            raise DensityNumericalInputError("grid_shape entries must be positive integers.")
        item = int(entry)
        if item <= 0:
            raise DensityNumericalInputError("grid_shape entries must be positive integers.")
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


def _rms_from_covariance(covariance: FloatArray) -> float:
    trace = float(np.trace(covariance))
    tolerance = 256.0 * np.finfo(np.float64).eps * max(
        1.0, float(np.max(np.abs(covariance)))
    )
    if trace < -tolerance:
        raise DensityNumericalInputError("Artificial covariance has a negative trace.")
    return float(np.sqrt(max(0.0, trace) / 3.0))


@dataclass(frozen=True, slots=True)
class ArtificialBroadeningDiagnostic:
    """Phase-weighted CIC and canonical-stencil covariance diagnostic."""

    grid_shape: tuple[int, int, int]
    sample_count: int
    source_weight_sum: float
    phase_variance_coefficients: FloatArray
    cic_covariance: FloatArray
    stencil_covariance: FloatArray
    total_covariance: FloatArray
    cic_rms: float
    stencil_rms: float
    effective_rms: float
    stencil_moments: PeriodicGaussianStencilMoments
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_BROADENING_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_BROADENING_SCHEMA:
            raise DensityNumericalInputError(
                f"Unsupported artificial-broadening schema {self.schema_version!r}."
            )
        shape = _validated_shape(self.grid_shape)
        sample_count = int(self.sample_count)
        weight_sum = float(self.source_weight_sum)
        if sample_count <= 0:
            raise DensityNumericalInputError("sample_count must be positive.")
        if not np.isfinite(weight_sum) or weight_sum <= 0.0:
            raise DensityNumericalInputError("source_weight_sum must be finite and positive.")
        phase = _readonly_array(
            self.phase_variance_coefficients,
            shape=(3,),
            name="phase_variance_coefficients",
        )
        if np.any(phase < 0.0) or np.any(phase > 0.25 + 5.0e-15):
            raise DensityNumericalInputError(
                "phase_variance_coefficients must lie in [0, 1/4]."
            )
        cic = _readonly_array(
            self.cic_covariance, shape=(3, 3), name="cic_covariance"
        )
        stencil = _readonly_array(
            self.stencil_covariance,
            shape=(3, 3),
            name="stencil_covariance",
        )
        total = _readonly_array(
            self.total_covariance, shape=(3, 3), name="total_covariance"
        )
        for name, covariance in (
            ("cic_covariance", cic),
            ("stencil_covariance", stencil),
            ("total_covariance", total),
        ):
            symmetry_error = float(np.max(np.abs(covariance - covariance.T)))
            if symmetry_error > 5.0e-13 * max(
                1.0, float(np.max(np.abs(covariance)))
            ):
                raise DensityNumericalInputError(f"{name} must be symmetric.")
        addition_error = float(np.max(np.abs(total - (cic + stencil))))
        if addition_error > 5.0e-13 * max(1.0, float(np.max(np.abs(total)))):
            raise DensityNumericalInputError(
                "total_covariance must equal CIC plus stencil covariance."
            )
        computed_cic = _rms_from_covariance(cic)
        computed_stencil = _rms_from_covariance(stencil)
        computed_effective = _rms_from_covariance(total)
        supplied = (
            float(self.cic_rms),
            float(self.stencil_rms),
            float(self.effective_rms),
        )
        computed = (computed_cic, computed_stencil, computed_effective)
        for name, value, expected in zip(
            ("cic_rms", "stencil_rms", "effective_rms"),
            supplied,
            computed,
            strict=True,
        ):
            if not np.isfinite(value) or value < 0.0:
                raise DensityNumericalInputError(f"{name} must be finite and nonnegative.")
            if abs(value - expected) > 5.0e-13 * max(1.0, expected):
                raise DensityNumericalInputError(f"{name} is inconsistent with covariance.")
        if not isinstance(self.stencil_moments, PeriodicGaussianStencilMoments):
            raise TypeError("stencil_moments must be PeriodicGaussianStencilMoments.")
        if self.stencil_moments.grid_shape != shape:
            raise DensityNumericalInputError("stencil_moments grid shape is inconsistent.")
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "sample_count", sample_count)
        object.__setattr__(self, "source_weight_sum", weight_sum)
        object.__setattr__(self, "phase_variance_coefficients", phase)
        object.__setattr__(self, "cic_covariance", cic)
        object.__setattr__(self, "stencil_covariance", stencil)
        object.__setattr__(self, "total_covariance", total)
        object.__setattr__(self, "cic_rms", computed_cic)
        object.__setattr__(self, "stencil_rms", computed_stencil)
        object.__setattr__(self, "effective_rms", computed_effective)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def metadata_dict(self) -> dict[str, Any]:
        return {
            **self.metadata.to_json_dict(),
            "artificial_broadening_schema": self.schema_version,
            "broadening_metric": EFFECTIVE_CIC_STENCIL_BROADENING,
            "broadening_sample_count": self.sample_count,
            "broadening_source_weight_sum": self.source_weight_sum,
            "cic_phase_variance_coefficients": self.phase_variance_coefficients.tolist(),
            "cic_covariance_cartesian": self.cic_covariance.tolist(),
            "stencil_covariance_cartesian": self.stencil_covariance.tolist(),
            "artificial_covariance_cartesian": self.total_covariance.tolist(),
            "cic_assignment_rms": self.cic_rms,
            "canonical_stencil_rms": self.stencil_rms,
            "effective_artificial_rms": self.effective_rms,
        }


def cic_assignment_covariance(
    fractional_positions: Any,
    sample_weights: Any,
    grid_shape: tuple[int, int, int],
    display_cell: Any,
) -> tuple[FloatArray, FloatArray, float]:
    """Return weighted periodic CIC covariance and phase coefficients."""

    positions = np.asarray(fractional_positions, dtype=np.float64)
    weights = np.asarray(sample_weights, dtype=np.float64)
    shape = _validated_shape(grid_shape)
    cell = _validated_cell(display_cell)
    if positions.ndim != 2 or positions.shape[1] != 3 or positions.shape[0] < 1:
        raise DensityNumericalInputError(
            "fractional_positions must have shape (n_samples, 3) and be nonempty."
        )
    if np.any(~np.isfinite(positions)):
        raise DensityNumericalInputError("fractional_positions must be finite.")
    if weights.shape != (positions.shape[0],) or np.any(~np.isfinite(weights)):
        raise DensityNumericalInputError("sample_weights must align with fractional_positions.")
    if np.any(weights < 0.0):
        raise DensityNumericalInputError("sample_weights must be nonnegative.")
    weight_sum = float(np.sum(weights, dtype=np.float64))
    if not np.isfinite(weight_sum) or weight_sum <= 0.0:
        raise DensityNumericalInputError("sample_weights must have positive total weight.")

    folded = positions - np.floor(positions)
    scaled = folded * np.asarray(shape, dtype=np.float64)[None, :]
    phase = scaled - np.floor(scaled)
    normalized = weights / weight_sum
    coefficients = np.einsum(
        "n,na->a", normalized, phase * (1.0 - phase), optimize=True
    )
    basis = cell / np.asarray(shape, dtype=np.float64)[:, None]
    covariance = np.einsum(
        "a,ai,aj->ij", coefficients, basis, basis, optimize=True
    )
    covariance = 0.5 * (covariance + covariance.T)
    return covariance, coefficients, weight_sum


def effective_artificial_broadening(
    fractional_positions: Any,
    sample_weights: Any,
    grid_shape: tuple[int, int, int],
    display_cell: Any,
    gaussian_bandwidth: float,
    *,
    kernel_tail_tolerance: float = 1.0e-8,
    max_candidate_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ArtificialBroadeningDiagnostic:
    """Return ``effective_cic_stencil_rms_v1`` for one weighted sample batch."""

    positions = np.asarray(fractional_positions, dtype=np.float64)
    cic, coefficients, weight_sum = cic_assignment_covariance(
        positions,
        sample_weights,
        grid_shape,
        display_cell,
    )
    moments = periodic_gaussian_stencil_moments(
        grid_shape,
        display_cell,
        gaussian_bandwidth,
        kernel_tail_tolerance=kernel_tail_tolerance,
        max_candidate_contributions=max_candidate_contributions,
        max_workspace_bytes=max_workspace_bytes,
    )
    total = cic + moments.covariance
    total = 0.5 * (total + total.T)
    return ArtificialBroadeningDiagnostic(
        grid_shape=grid_shape,
        sample_count=int(positions.shape[0]),
        source_weight_sum=weight_sum,
        phase_variance_coefficients=coefficients,
        cic_covariance=cic,
        stencil_covariance=moments.covariance,
        total_covariance=total,
        cic_rms=_rms_from_covariance(cic),
        stencil_rms=_rms_from_covariance(moments.covariance),
        effective_rms=_rms_from_covariance(total),
        stencil_moments=moments,
        metadata={} if metadata is None else metadata,
    )
