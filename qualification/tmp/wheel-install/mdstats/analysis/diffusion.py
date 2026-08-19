"""Explicit diffusion estimation and MSD/VACF consistency diagnostics.

Einstein's displacement relation and the Green-Kubo velocity-correlation
relation provide the physical comparison.  Interval selection, centered OLS,
semantic signatures, explicit subspace handling, and fail-closed provenance
checks are mdstats design decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._dynamics_common import (
    AnalysisSubspace,
    AxisLabel,
    DynamicsInputSignature,
    freeze_mapping,
    owned_readonly_array,
    project_trace_from_result,
)
from .msd import MSDResult
from .vacf_transport import VACFDiffusionResult

FloatArray = NDArray[np.float64]
PlateauMethod = Literal["explicit", "stable_window"]
_A2_PER_PS_TO_CM2_PER_S = 1.0e-4


def _result_subspace(
    *,
    projection_basis: ArrayLike | None,
    projection_labels: tuple[AxisLabel, ...] | None,
    component: str,
    dimensions: int,
) -> AnalysisSubspace:
    from ._dynamics_common import resolve_analysis_subspace

    if projection_basis is not None:
        basis = np.asarray(projection_basis, dtype=np.float64)
        if basis.ndim == 1:
            basis = basis.reshape(1, -1)
        return AnalysisSubspace(basis, projection_labels, int(basis.shape[0]))
    if component in ("x", "y", "z"):
        return resolve_analysis_subspace(axes=(component,))  # type: ignore[arg-type]
    if dimensions == 3:
        return resolve_analysis_subspace()
    return resolve_analysis_subspace(
        axes=("x",) if dimensions == 1 else ("x", "y")
    )


@dataclass(frozen=True, slots=True)
class DiffusionEstimate:
    """Explicit estimate from a selected running Green-Kubo interval."""

    value_a2_per_ps: float
    standard_error_a2_per_ps: float | None
    time_range_ps: tuple[float, float]
    method: str
    component: str
    dimensions: int
    n_points: int
    is_stable: bool | None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    projection_basis: FloatArray | None = None
    projection_labels: tuple[AxisLabel, ...] | None = None
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        value = float(self.value_a2_per_ps)
        if not np.isfinite(value):
            raise ValueError("value_a2_per_ps must be finite.")
        standard_error = (
            None
            if self.standard_error_a2_per_ps is None
            else float(self.standard_error_a2_per_ps)
        )
        if standard_error is not None and (
            not np.isfinite(standard_error) or standard_error < 0.0
        ):
            raise ValueError("standard_error_a2_per_ps must be nonnegative or None.")
        if not isinstance(self.time_range_ps, tuple) or len(self.time_range_ps) != 2:
            raise TypeError("time_range_ps must be a two-element tuple.")
        start, end = map(float, self.time_range_ps)
        if not np.isfinite(start) or not np.isfinite(end) or end <= start:
            raise ValueError("time_range_ps must contain finite values with end > start.")
        if self.method != "explicit":
            raise ValueError("Only method='explicit' is represented in G2 results.")
        if self.component not in ("scalar", "x", "y", "z"):
            raise ValueError("component must be 'scalar', 'x', 'y', or 'z'.")
        if isinstance(self.dimensions, (bool, np.bool_)) or not isinstance(
            self.dimensions, (int, np.integer)
        ):
            raise TypeError("dimensions must be an integer.")
        dimensions = int(self.dimensions)
        if dimensions not in (1, 2, 3):
            raise ValueError("dimensions must be 1, 2, or 3.")
        if isinstance(self.n_points, (bool, np.bool_)) or not isinstance(
            self.n_points, (int, np.integer)
        ):
            raise TypeError("n_points must be an integer.")
        n_points = int(self.n_points)
        if n_points < 2:
            raise ValueError("n_points must be at least two.")
        if self.is_stable is not None and not isinstance(
            self.is_stable, (bool, np.bool_)
        ):
            raise TypeError("is_stable must be bool or None.")
        subspace = _result_subspace(
            projection_basis=self.projection_basis,
            projection_labels=self.projection_labels,
            component=self.component,
            dimensions=dimensions,
        )
        if subspace.rank != dimensions or subspace.component_label != self.component:
            raise ValueError("Diffusion estimate subspace fields are inconsistent.")
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not self.signature.subspace.same_physical_subspace(subspace):
                raise ValueError("signature projection is inconsistent with the estimate.")

        object.__setattr__(self, "value_a2_per_ps", value)
        object.__setattr__(self, "standard_error_a2_per_ps", standard_error)
        object.__setattr__(self, "time_range_ps", (start, end))
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "n_points", n_points)
        object.__setattr__(
            self,
            "is_stable",
            None if self.is_stable is None else bool(self.is_stable),
        )
        object.__setattr__(self, "projection_basis", subspace.projection_basis)
        object.__setattr__(self, "projection_labels", subspace.labels)
        object.__setattr__(self, "diagnostics", freeze_mapping(self.diagnostics))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))

    @property
    def value_cm2_per_s(self) -> float:
        return self.value_a2_per_ps * _A2_PER_PS_TO_CM2_PER_S

    @property
    def standard_error_cm2_per_s(self) -> float | None:
        if self.standard_error_a2_per_ps is None:
            return None
        return self.standard_error_a2_per_ps * _A2_PER_PS_TO_CM2_PER_S


@dataclass(frozen=True, slots=True)
class DiffusionComparisonResult:
    """Comparison of explicit projected MSD and VACF diffusion estimates."""

    msd_diffusion_a2_per_ps: float
    vacf_diffusion_a2_per_ps: float
    signed_difference_a2_per_ps: float
    absolute_difference_a2_per_ps: float
    symmetric_relative_difference: float
    msd_fit_range_ps: tuple[float, float]
    msd_slope_a2_per_ps: float
    msd_intercept_a2: float
    component: str
    dimensions: int
    n_msd_points: int
    diagnostics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    projection_basis: FloatArray | None = None
    projection_labels: tuple[AxisLabel, ...] | None = None
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        scalar_names = (
            "msd_diffusion_a2_per_ps",
            "vacf_diffusion_a2_per_ps",
            "signed_difference_a2_per_ps",
            "absolute_difference_a2_per_ps",
            "symmetric_relative_difference",
            "msd_slope_a2_per_ps",
            "msd_intercept_a2",
        )
        resolved: dict[str, float] = {}
        for name in scalar_names:
            value = float(getattr(self, name))
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")
            resolved[name] = value
        if resolved["absolute_difference_a2_per_ps"] < 0.0:
            raise ValueError("absolute_difference_a2_per_ps must be nonnegative.")
        if resolved["symmetric_relative_difference"] < 0.0:
            raise ValueError("symmetric_relative_difference must be nonnegative.")
        if not isinstance(self.msd_fit_range_ps, tuple) or len(self.msd_fit_range_ps) != 2:
            raise TypeError("msd_fit_range_ps must be a two-element tuple.")
        start, end = map(float, self.msd_fit_range_ps)
        if not np.isfinite(start) or not np.isfinite(end) or end <= start:
            raise ValueError("msd_fit_range_ps must contain finite values with end > start.")
        if self.component not in ("scalar", "x", "y", "z"):
            raise ValueError("component must be 'scalar', 'x', 'y', or 'z'.")
        if isinstance(self.dimensions, (bool, np.bool_)) or not isinstance(
            self.dimensions, (int, np.integer)
        ):
            raise TypeError("dimensions must be an integer.")
        dimensions = int(self.dimensions)
        if dimensions not in (1, 2, 3):
            raise ValueError("dimensions must be 1, 2, or 3.")
        if isinstance(self.n_msd_points, (bool, np.bool_)) or not isinstance(
            self.n_msd_points, (int, np.integer)
        ):
            raise TypeError("n_msd_points must be an integer.")
        n_points = int(self.n_msd_points)
        if n_points < 3:
            raise ValueError("n_msd_points must be at least three.")
        subspace = _result_subspace(
            projection_basis=self.projection_basis,
            projection_labels=self.projection_labels,
            component=self.component,
            dimensions=dimensions,
        )
        if subspace.rank != dimensions or subspace.component_label != self.component:
            raise ValueError("Diffusion comparison subspace fields are inconsistent.")

        expected_signed = (
            resolved["msd_diffusion_a2_per_ps"]
            - resolved["vacf_diffusion_a2_per_ps"]
        )
        denominator = (
            abs(resolved["msd_diffusion_a2_per_ps"])
            + abs(resolved["vacf_diffusion_a2_per_ps"])
        )
        expected_relative = (
            0.0 if denominator == 0.0 else 2.0 * abs(expected_signed) / denominator
        )
        if not np.isclose(resolved["signed_difference_a2_per_ps"], expected_signed):
            raise ValueError("signed_difference_a2_per_ps is inconsistent.")
        if not np.isclose(
            resolved["absolute_difference_a2_per_ps"], abs(expected_signed)
        ):
            raise ValueError("absolute_difference_a2_per_ps is inconsistent.")
        if not np.isclose(
            resolved["symmetric_relative_difference"], expected_relative
        ):
            raise ValueError("symmetric_relative_difference is inconsistent.")
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not self.signature.subspace.same_physical_subspace(subspace):
                raise ValueError("signature projection is inconsistent with comparison.")

        for name, value in resolved.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "msd_fit_range_ps", (start, end))
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "n_msd_points", n_points)
        object.__setattr__(self, "projection_basis", subspace.projection_basis)
        object.__setattr__(self, "projection_labels", subspace.labels)
        object.__setattr__(self, "diagnostics", freeze_mapping(self.diagnostics))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))

    @property
    def msd_diffusion_cm2_per_s(self) -> float:
        return self.msd_diffusion_a2_per_ps * _A2_PER_PS_TO_CM2_PER_S

    @property
    def vacf_diffusion_cm2_per_s(self) -> float:
        return self.vacf_diffusion_a2_per_ps * _A2_PER_PS_TO_CM2_PER_S

    @property
    def absolute_difference_cm2_per_s(self) -> float:
        return self.absolute_difference_a2_per_ps * _A2_PER_PS_TO_CM2_PER_S


def _validate_interval(
    values: tuple[float, float] | None,
    *,
    name: str,
    available_start: float,
    available_end: float,
) -> tuple[float, float]:
    if values is None:
        raise ValueError(f"{name} is required for the explicit method.")
    if not isinstance(values, tuple) or len(values) != 2:
        raise TypeError(f"{name} must be a two-element tuple.")
    for item in values:
        if isinstance(item, (bool, np.bool_)) or not isinstance(
            item, (int, float, np.integer, np.floating)
        ):
            raise TypeError(f"{name} entries must be real numbers.")
    start, end = map(float, values)
    if not np.isfinite(start) or not np.isfinite(end) or end <= start:
        raise ValueError(f"{name} must contain finite values with end > start.")
    tolerance = 64.0 * np.finfo(np.float64).eps * max(
        1.0, abs(available_start), abs(available_end), abs(start), abs(end)
    )
    if start < available_start - tolerance or end > available_end + tolerance:
        raise ValueError(
            f"{name}={values!r} lies outside the available interval "
            f"[{available_start}, {available_end}]."
        )
    return start, end


def _select_interval(coordinates: np.ndarray, requested: tuple[float, float]) -> np.ndarray:
    start, end = requested
    tolerance = 64.0 * np.finfo(np.float64).eps * max(
        1.0, abs(start), abs(end), abs(float(coordinates[-1]))
    )
    return np.flatnonzero(
        (coordinates >= start - tolerance) & (coordinates <= end + tolerance)
    )


def _require_uniform_selected_grid(times: np.ndarray) -> float:
    if times.size < 2:
        raise ValueError("At least two selected time samples are required.")
    increments = np.diff(times)
    if not np.allclose(
        increments,
        increments[0],
        rtol=1.0e-10,
        atol=max(1.0e-14, 1.0e-12 * abs(float(increments[0]))),
    ):
        raise ValueError(
            "The selected plateau samples must be uniformly spaced for the "
            "arithmetic-mean estimator."
        )
    return float(increments[0])


def _centered_linear_diagnostics(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[float, float, float, float]:
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    xc = x - x_mean
    yc = y - y_mean
    denominator = float(np.dot(xc, xc))
    if denominator <= 0.0:
        raise ValueError("The selected time coordinates do not span a fit interval.")
    slope = float(np.dot(xc, yc) / denominator)
    intercept = float(y_mean - slope * x_mean)
    residual = y - (intercept + slope * x)
    residual_rms = float(np.sqrt(np.mean(residual * residual)))
    total = float(np.dot(yc, yc))
    r_squared = 1.0 if total == 0.0 and residual_rms == 0.0 else (
        0.0 if total == 0.0 else float(1.0 - np.dot(residual, residual) / total)
    )
    return slope, intercept, r_squared, residual_rms


def estimate_diffusion_plateau(
    running: VACFDiffusionResult,
    *,
    time_range_ps: tuple[float, float] | None = None,
    minimum_points: int = 8,
    slope_tolerance: float | None = None,
    method: PlateauMethod = "explicit",
) -> DiffusionEstimate:
    """Estimate diffusion over an explicit uniformly sampled running interval."""

    if not isinstance(running, VACFDiffusionResult):
        raise TypeError("running must be a VACFDiffusionResult instance.")
    if method == "stable_window":
        raise NotImplementedError(
            "method='stable_window' is deferred until a separately specified "
            "automatic-window validation stage."
        )
    if method != "explicit":
        raise ValueError("method must be 'explicit' or 'stable_window'.")
    if isinstance(minimum_points, (bool, np.bool_)) or not isinstance(
        minimum_points, (int, np.integer)
    ):
        raise TypeError("minimum_points must be an integer.")
    minimum = int(minimum_points)
    if minimum < 2:
        raise ValueError("minimum_points must be at least two.")
    if slope_tolerance is not None:
        if isinstance(slope_tolerance, (bool, np.bool_)) or not isinstance(
            slope_tolerance, (int, float, np.integer, np.floating)
        ):
            raise TypeError("slope_tolerance must be a real number or None.")
        slope_tolerance = float(slope_tolerance)
        if not np.isfinite(slope_tolerance) or slope_tolerance < 0.0:
            raise ValueError("slope_tolerance must be finite and nonnegative.")

    times = np.asarray(running.lag_times, dtype=np.float64)
    values = np.asarray(running.running_diffusion_a2_per_ps, dtype=np.float64)
    requested = _validate_interval(
        time_range_ps,
        name="time_range_ps",
        available_start=float(times[0]),
        available_end=float(times[-1]),
    )
    selected = _select_interval(times, requested)
    if selected.size < minimum:
        raise ValueError(
            f"The requested interval contains {selected.size} stored samples; "
            f"minimum_points={minimum}."
        )
    selected_times = times[selected]
    selected_values = values[selected]
    selected_spacing = _require_uniform_selected_grid(selected_times)
    slope, intercept, r_squared, residual_rms = _centered_linear_diagnostics(
        selected_times, selected_values
    )
    estimate = float(np.mean(selected_values))
    actual_range = (float(selected_times[0]), float(selected_times[-1]))
    is_stable = (
        None if slope_tolerance is None else bool(abs(slope) <= slope_tolerance)
    )
    diagnostics: dict[str, Any] = {
        "interval_mean_a2_per_ps": estimate,
        "interval_median_a2_per_ps": float(np.median(selected_values)),
        "interval_sample_standard_deviation_a2_per_ps": float(
            np.std(selected_values, ddof=1)
        ),
        "interval_minimum_a2_per_ps": float(np.min(selected_values)),
        "interval_maximum_a2_per_ps": float(np.max(selected_values)),
        "interval_span_a2_per_ps": float(np.ptp(selected_values)),
        "endpoint_drift_a2_per_ps": float(selected_values[-1] - selected_values[0]),
        "linear_slope_a2_per_ps2": slope,
        "linear_intercept_a2_per_ps": intercept,
        "linear_r_squared": r_squared,
        "linear_residual_rms_a2_per_ps": residual_rms,
        "selected_sample_spacing_ps": selected_spacing,
        "slope_tolerance_a2_per_ps2": slope_tolerance,
        "passes_slope_tolerance": is_stable,
        "uncertainty_policy": (
            "no_independent_sample_standard_error_from_one_serially_correlated_"
            "running_curve"
        ),
        "automatic_plateau_search": False,
        "tail_fit": False,
    }
    metadata: dict[str, Any] = {
        "schema": "mdstats.diffusion_estimate.v2",
        "requested_time_range_ps": requested,
        "actual_time_range_ps": actual_range,
        "selected_indices": selected.tolist(),
        "source_component": running.component,
        "source_dimensions": running.dimensions,
        "projection_basis": running.projection_basis,
        "projection_labels": running.projection_labels,
        "source_weighting": running.weighting,
        "source_integration": running.integration,
        "selected_atom_indices": running.metadata.get("selected_atom_indices", ()),
        "drift_mode": running.metadata.get("drift_mode"),
        "drift_atom_indices": running.metadata.get("drift_atom_indices"),
        "source_running_metadata": running.metadata,
        "canonical_units": "Å^2/ps",
        "cm2_per_s_conversion": _A2_PER_PS_TO_CM2_PER_S,
        "plateau_method_is_mdstats_design": True,
        "signature_complete": running.signature is not None,
    }
    return DiffusionEstimate(
        value_a2_per_ps=estimate,
        standard_error_a2_per_ps=None,
        time_range_ps=actual_range,
        method="explicit",
        component=running.component,
        dimensions=running.dimensions,
        n_points=int(selected.size),
        is_stable=is_stable,
        diagnostics=diagnostics,
        metadata=metadata,
        projection_basis=running.projection_basis,
        projection_labels=running.projection_labels,
        signature=running.signature,
    )


def _require_comparable_results(
    msd: MSDResult,
    estimate: DiffusionEstimate,
) -> AnalysisSubspace:
    if msd.mode != "time_averaged":
        raise ValueError(
            "MSD/VACF diffusion comparison requires mode='time_averaged'; "
            "fixed-origin MSD is nonstationary."
        )
    if msd.coordinate_mode != "laboratory":
        raise ValueError(
            "MSD/VACF diffusion comparison currently requires laboratory-frame "
            "MSD coordinates to match Cartesian velocities."
        )
    if msd.signature is None or estimate.signature is None:
        raise ValueError(
            "MSD/VACF comparison requires complete DynamicsInputSignature "
            "provenance; legacy unsigned results are not comparable by default."
        )
    subspace = AnalysisSubspace(
        estimate.projection_basis,
        estimate.projection_labels,
        estimate.dimensions,
    )
    projected_msd_signature = msd.signature.with_subspace(subspace)
    mismatches = projected_msd_signature.mismatch_fields(estimate.signature)
    if mismatches:
        raise ValueError(
            "MSD and VACF estimates have incompatible dynamics provenance: "
            + ", ".join(mismatches)
            + "."
        )
    return subspace


def compare_msd_vacf_diffusion(
    msd: MSDResult,
    vacf_diffusion: DiffusionEstimate,
    *,
    msd_fit_range_ps: tuple[float, float],
    dimensions: Literal[1, 2, 3] | None = None,
) -> DiffusionComparisonResult:
    """Compare projected Einstein-MSD and Green-Kubo estimates.

    ``dimensions`` is a deprecated consistency check only.  The physical rank
    is derived from the stored projection basis and cannot reinterpret data.
    """

    if not isinstance(msd, MSDResult):
        raise TypeError("msd must be an MSDResult instance.")
    if not isinstance(vacf_diffusion, DiffusionEstimate):
        raise TypeError("vacf_diffusion must be a DiffusionEstimate instance.")
    if dimensions is not None:
        if isinstance(dimensions, (bool, np.bool_)) or not isinstance(
            dimensions, (int, np.integer)
        ):
            raise TypeError("dimensions must be an integer or None.")
        if int(dimensions) not in (1, 2, 3):
            raise ValueError("dimensions must be 1, 2, or 3.")
        if int(dimensions) != vacf_diffusion.dimensions:
            raise ValueError(
                "dimensions is inconsistent with the stored analysis subspace."
            )
    subspace = _require_comparable_results(msd, vacf_diffusion)

    times = np.asarray(msd.lag_times, dtype=np.float64)
    requested = _validate_interval(
        msd_fit_range_ps,
        name="msd_fit_range_ps",
        available_start=float(times[0]),
        available_end=float(times[-1]),
    )
    selected = _select_interval(times, requested)
    if selected.size < 3:
        raise ValueError("The MSD fit interval must contain at least three stored samples.")
    selected_times = times[selected]
    selected_msd = project_trace_from_result(
        components=msd.components[selected],
        tensor=None if msd.tensor is None else msd.tensor[selected],
        subspace=subspace,
        tensor_name="MSD tensor",
    )
    slope, intercept, r_squared, residual_rms = _centered_linear_diagnostics(
        selected_times, selected_msd
    )
    divisor = 2.0 * float(subspace.rank)
    msd_diffusion = slope / divisor
    vacf_value = float(vacf_diffusion.value_a2_per_ps)
    signed = msd_diffusion - vacf_value
    absolute = abs(signed)
    denominator = abs(msd_diffusion) + abs(vacf_value)
    relative = 0.0 if denominator == 0.0 else 2.0 * absolute / denominator
    actual_range = (float(selected_times[0]), float(selected_times[-1]))

    flags: list[str] = []
    if slope <= 0.0:
        flags.append("nonpositive_msd_slope")
    if vacf_diffusion.is_stable is False:
        flags.append("vacf_interval_failed_slope_tolerance")
    elif vacf_diffusion.is_stable is None:
        flags.append("vacf_interval_stability_not_assessed")
    diagnostics: dict[str, Any] = {
        "msd_linear_r_squared": r_squared,
        "msd_linear_residual_rms_a2": residual_rms,
        "msd_fit_divisor": divisor,
        "msd_endpoint_change_a2": float(selected_msd[-1] - selected_msd[0]),
        "vacf_plateau_is_stable": vacf_diffusion.is_stable,
        "vacf_plateau_standard_error_a2_per_ps": (
            vacf_diffusion.standard_error_a2_per_ps
        ),
        "interpretation_flags": flags,
        "automatic_regime_classification": False,
        "one_estimator_declared_authoritative": False,
    }
    metadata: dict[str, Any] = {
        "schema": "mdstats.diffusion_comparison.v2",
        "requested_msd_fit_range_ps": requested,
        "actual_msd_fit_range_ps": actual_range,
        "selected_msd_indices": selected.tolist(),
        "selected_atom_indices": msd.atom_indices.tolist(),
        "drift_mode": msd.drift_mode,
        "drift_atom_indices": msd.signature.drift_atom_indices,
        "coordinate_mode": msd.coordinate_mode,
        "projection_basis": subspace.projection_basis,
        "projection_labels": subspace.labels,
        "source_msd_metadata": msd.metadata,
        "source_vacf_estimate_metadata": vacf_diffusion.metadata,
        "einstein_reference": "Einstein 1905, DOI:10.1002/andp.19053220806",
        "green_kubo_references": (
            "Green 1954, DOI:10.1063/1.1740082",
            "Kubo 1957, DOI:10.1143/JPSJ.12.570",
        ),
        "msd_fit_method": "centered ordinary least squares with intercept",
        "relative_difference_definition": (
            "2*abs(D_msd-D_vacf)/(abs(D_msd)+abs(D_vacf))"
        ),
        "canonical_units": "Å^2/ps",
        "cm2_per_s_conversion": _A2_PER_PS_TO_CM2_PER_S,
        "signature_complete": True,
    }
    return DiffusionComparisonResult(
        msd_diffusion_a2_per_ps=msd_diffusion,
        vacf_diffusion_a2_per_ps=vacf_value,
        signed_difference_a2_per_ps=signed,
        absolute_difference_a2_per_ps=absolute,
        symmetric_relative_difference=relative,
        msd_fit_range_ps=actual_range,
        msd_slope_a2_per_ps=slope,
        msd_intercept_a2=intercept,
        component=subspace.component_label,
        dimensions=subspace.rank,
        n_msd_points=int(selected.size),
        diagnostics=diagnostics,
        metadata=metadata,
        projection_basis=subspace.projection_basis,
        projection_labels=subspace.labels,
        signature=vacf_diffusion.signature,
    )
