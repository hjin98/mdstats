"""Green-Kubo transport curves derived from a stored self VACF.

The self-diffusion relation follows Green [J. Chem. Phys. 22, 398-413
(1954), DOI: 10.1063/1.1740082] and Kubo [J. Phys. Soc. Jpn. 12,
570-586 (1957), DOI: 10.1143/JPSJ.12.570].  The equivalence between
correlation and displacement representations is part of the Einstein-Helfand
lineage [Helfand, Phys. Rev. 119, 1-9 (1960), DOI: 10.1103/PhysRev.119.1].

H0 adds explicit physical-subspace selection, complete semantic signatures,
and deeply immutable result objects.  These API and provenance contracts are
mdstats design rather than borrowed physical estimators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._dynamics_common import (
    AnalysisSubspace,
    AxisLabel,
    DynamicsInputSignature,
    freeze_mapping,
    owned_readonly_array,
    project_trace_from_result,
    resolve_subspace_with_legacy_options,
)
from ._quadrature import cumulative_trapezoid_zero
from .vacf import VACFResult

FloatArray = NDArray[np.float64]
DiffusionComponent = Literal["scalar", "x", "y", "z"]
IntegrationMethod = Literal["trapezoid"]

_A2_PER_PS_TO_CM2_PER_S = 1.0e-4


def _legacy_subspace(
    projection_basis: ArrayLike | None,
    projection_labels: tuple[AxisLabel, ...] | None,
    *,
    dimensions: int,
    component: str,
) -> AnalysisSubspace:
    """Resolve result construction, including explicitly unsigned legacy data."""

    if projection_basis is not None:
        from ._dynamics_common import AnalysisSubspace

        basis = np.asarray(projection_basis, dtype=np.float64)
        if basis.ndim == 1:
            basis = basis.reshape(1, -1)
        return AnalysisSubspace(basis, projection_labels, int(basis.shape[0]))
    if component in ("x", "y", "z"):
        return resolve_subspace_with_legacy_options(
            axes=None,
            projection_basis=None,
            component=component,
            dimensions=1,
        )
    if dimensions == 3:
        return resolve_subspace_with_legacy_options(
            axes=None,
            projection_basis=None,
            component="scalar",
            dimensions=3,
        )
    # Legacy direct constructors may still be loaded, but they remain unsigned
    # and cannot pass H0 cross-module compatibility.  Use canonical x or xy as
    # a deterministic representation rather than silently claiming provenance.
    labels = ("x",) if dimensions == 1 else ("x", "y")
    return resolve_subspace_with_legacy_options(
        axes=labels,
        projection_basis=None,
        component="scalar",
        dimensions=dimensions,
    )


@dataclass(frozen=True, slots=True)
class VACFDiffusionResult:
    """Running Green-Kubo self-diffusion integral and exact provenance."""

    lag_times: FloatArray
    running_diffusion_a2_per_ps: FloatArray
    integrand: FloatArray
    dimensions: int
    component: str
    weighting: str
    integration: str
    metadata: dict[str, Any] = field(default_factory=dict)
    projection_basis: FloatArray | None = None
    projection_labels: tuple[AxisLabel, ...] | None = None
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        lag_times = np.asarray(self.lag_times, dtype=np.float64)
        running = np.asarray(self.running_diffusion_a2_per_ps, dtype=np.float64)
        integrand = np.asarray(self.integrand, dtype=np.float64)
        if lag_times.ndim != 1 or lag_times.size < 1:
            raise ValueError("lag_times must be a nonempty one-dimensional array.")
        if running.shape != lag_times.shape or integrand.shape != lag_times.shape:
            raise ValueError("running diffusion and integrand must match lag_times.")
        if not all(np.all(np.isfinite(v)) for v in (lag_times, running, integrand)):
            raise ValueError("VACF diffusion results must contain only finite values.")
        if not np.isclose(lag_times[0], 0.0, rtol=0.0, atol=1.0e-14):
            raise ValueError("lag_times must start at zero.")
        if lag_times.size > 1 and np.any(np.diff(lag_times) <= 0.0):
            raise ValueError("lag_times must be strictly increasing.")
        if not np.isclose(running[0], 0.0, rtol=0.0, atol=1.0e-14):
            raise ValueError("The running diffusion curve must start at zero.")
        if isinstance(self.dimensions, (bool, np.bool_)) or not isinstance(
            self.dimensions, (int, np.integer)
        ):
            raise TypeError("dimensions must be an integer.")
        dimensions = int(self.dimensions)
        if dimensions not in (1, 2, 3):
            raise ValueError("dimensions must be 1, 2, or 3.")
        if self.component not in ("scalar", "x", "y", "z"):
            raise ValueError("component must be 'scalar', 'x', 'y', or 'z'.")
        if self.projection_basis is None and self.component in ("x", "y", "z"):
            dimensions = 1
        if self.weighting not in ("uniform", "explicit_uniform"):
            raise ValueError("Unsupported physical self-diffusion weighting label.")
        if self.integration != "trapezoid":
            raise ValueError("Only trapezoidal integration is currently supported.")

        subspace = _legacy_subspace(
            self.projection_basis,
            self.projection_labels,
            dimensions=dimensions,
            component=self.component,
        )
        if subspace.rank != dimensions:
            raise ValueError("dimensions is inconsistent with projection_basis.")
        if self.component != subspace.component_label:
            raise ValueError("component is inconsistent with the resolved subspace.")
        expected_running = cumulative_trapezoid_zero(integrand, lag_times, axis=0)
        if not np.allclose(running, expected_running, rtol=2.0e-13, atol=2.0e-14):
            raise ValueError(
                "running_diffusion_a2_per_ps is inconsistent with the stored "
                "integrand and lag_times."
            )
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not self.signature.subspace.same_physical_subspace(subspace):
                raise ValueError("signature projection is inconsistent with the result.")

        object.__setattr__(self, "lag_times", owned_readonly_array(lag_times, dtype=np.float64))
        object.__setattr__(self, "running_diffusion_a2_per_ps", owned_readonly_array(running, dtype=np.float64))
        object.__setattr__(self, "integrand", owned_readonly_array(integrand, dtype=np.float64))
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "projection_basis", subspace.projection_basis)
        object.__setattr__(self, "projection_labels", subspace.labels)
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))

    @property
    def running_diffusion_cm2_per_s(self) -> FloatArray:
        result = self.running_diffusion_a2_per_ps * _A2_PER_PS_TO_CM2_PER_S
        return owned_readonly_array(result, dtype=np.float64)


@dataclass(frozen=True, slots=True)
class VACFMSDResult:
    """Mean-square displacement reconstructed from a physical self VACF."""

    lag_times: FloatArray
    reconstructed_msd_a2: FloatArray
    physical_vacf_a2_per_ps2: FloatArray
    cumulative_vacf_a2_per_ps: FloatArray
    cumulative_time_weighted_vacf_a2: FloatArray
    component: str
    weighting: str
    integration: str
    metadata: dict[str, Any] = field(default_factory=dict)
    dimensions: int = 3
    projection_basis: FloatArray | None = None
    projection_labels: tuple[AxisLabel, ...] | None = None
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        times = np.asarray(self.lag_times, dtype=np.float64)
        reconstructed = np.asarray(self.reconstructed_msd_a2, dtype=np.float64)
        physical = np.asarray(self.physical_vacf_a2_per_ps2, dtype=np.float64)
        i0 = np.asarray(self.cumulative_vacf_a2_per_ps, dtype=np.float64)
        i1 = np.asarray(self.cumulative_time_weighted_vacf_a2, dtype=np.float64)
        if times.ndim != 1 or times.size < 1:
            raise ValueError("lag_times must be a nonempty one-dimensional array.")
        if any(value.shape != times.shape for value in (reconstructed, physical, i0, i1)):
            raise ValueError("All VACF-MSD arrays must match lag_times.")
        if not all(np.all(np.isfinite(v)) for v in (times, reconstructed, physical, i0, i1)):
            raise ValueError("VACF-MSD results must contain only finite values.")
        if not np.isclose(times[0], 0.0, rtol=0.0, atol=1.0e-14):
            raise ValueError("lag_times must start at zero.")
        if times.size > 1 and np.any(np.diff(times) <= 0.0):
            raise ValueError("lag_times must be strictly increasing.")
        if any(not np.isclose(v[0], 0.0, rtol=0.0, atol=1.0e-14) for v in (reconstructed, i0, i1)):
            raise ValueError("Reconstructed MSD and cumulative moments must start at zero.")
        if isinstance(self.dimensions, (bool, np.bool_)) or not isinstance(
            self.dimensions, (int, np.integer)
        ):
            raise TypeError("dimensions must be an integer.")
        dimensions = int(self.dimensions)
        if dimensions not in (1, 2, 3):
            raise ValueError("dimensions must be 1, 2, or 3.")
        if self.component not in ("scalar", "x", "y", "z"):
            raise ValueError("component must be 'scalar', 'x', 'y', or 'z'.")
        if self.projection_basis is None and self.component in ("x", "y", "z"):
            dimensions = 1
        if self.weighting not in ("uniform", "explicit_uniform"):
            raise ValueError("Unsupported physical self-MSD weighting label.")
        if self.integration != "trapezoid":
            raise ValueError("Only trapezoidal integration is currently supported.")
        subspace = _legacy_subspace(
            self.projection_basis,
            self.projection_labels,
            dimensions=dimensions,
            component=self.component,
        )
        if subspace.rank != dimensions or self.component != subspace.component_label:
            raise ValueError("VACF-MSD subspace fields are inconsistent.")

        expected_i0 = cumulative_trapezoid_zero(physical, times, axis=0)
        expected_i1 = cumulative_trapezoid_zero(times * physical, times, axis=0)
        expected_msd = 2.0 * (times * expected_i0 - expected_i1)
        if not np.allclose(i0, expected_i0, rtol=2.0e-13, atol=2.0e-14):
            raise ValueError("cumulative_vacf_a2_per_ps is inconsistent.")
        if not np.allclose(i1, expected_i1, rtol=2.0e-13, atol=2.0e-14):
            raise ValueError("cumulative_time_weighted_vacf_a2 is inconsistent.")
        if not np.allclose(reconstructed, expected_msd, rtol=2.0e-13, atol=2.0e-14):
            raise ValueError("reconstructed_msd_a2 is inconsistent.")
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not self.signature.subspace.same_physical_subspace(subspace):
                raise ValueError("signature projection is inconsistent with the result.")

        object.__setattr__(self, "lag_times", owned_readonly_array(times, dtype=np.float64))
        object.__setattr__(self, "reconstructed_msd_a2", owned_readonly_array(reconstructed, dtype=np.float64))
        object.__setattr__(self, "physical_vacf_a2_per_ps2", owned_readonly_array(physical, dtype=np.float64))
        object.__setattr__(self, "cumulative_vacf_a2_per_ps", owned_readonly_array(i0, dtype=np.float64))
        object.__setattr__(self, "cumulative_time_weighted_vacf_a2", owned_readonly_array(i1, dtype=np.float64))
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "projection_basis", subspace.projection_basis)
        object.__setattr__(self, "projection_labels", subspace.labels)
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))


def _resolve_physical_weighting(vacf: VACFResult) -> str:
    """Require equal positive per-atom weights for self diffusion."""

    if vacf.weighting == "uniform":
        if np.allclose(vacf.atom_weights, 1.0, rtol=1.0e-13, atol=0.0):
            return "uniform"
        raise ValueError(
            "VACF weighting is labelled 'uniform' but atom_weights are not all "
            "one; the result is internally inconsistent for self diffusion."
        )
    if vacf.weighting == "explicit":
        reference = float(vacf.atom_weights[0])
        if reference > 0.0 and np.allclose(
            vacf.atom_weights, reference, rtol=1.0e-13, atol=0.0
        ):
            return "explicit_uniform"
        raise ValueError(
            "Self-diffusion requires equal positive per-atom weights; the "
            "explicit VACF weights are nonuniform."
        )
    if vacf.weighting == "mass":
        raise ValueError(
            "A mass-weighted VACF is not a physical self-diffusion integrand. "
            "Recompute the VACF with weights='uniform'."
        )
    raise ValueError(
        f"Unsupported VACF weighting {vacf.weighting!r}; self diffusion requires "
        "uniform or explicitly equal positive weights."
    )


def _validate_vacf_lag_times(vacf: VACFResult) -> FloatArray:
    times = np.asarray(vacf.lag_times, dtype=np.float64)
    if times.ndim != 1 or times.size < 1:
        raise ValueError("VACF lag_times must be a nonempty one-dimensional array.")
    if not np.all(np.isfinite(times)):
        raise ValueError("VACF lag_times must contain only finite values.")
    if not np.isclose(times[0], 0.0, rtol=0.0, atol=1.0e-14):
        raise ValueError("VACF lag_times must start at zero.")
    if times.size > 1 and np.any(np.diff(times) <= 0.0):
        raise ValueError("VACF lag_times must be strictly increasing.")
    return times


def _resolve_last_lag(lag_times: FloatArray, maximum_time_ps: float | None) -> int:
    if maximum_time_ps is None:
        return int(lag_times.size)
    if isinstance(maximum_time_ps, (bool, np.bool_)) or not isinstance(
        maximum_time_ps, (int, float, np.integer, np.floating)
    ):
        raise TypeError("maximum_time_ps must be a real number or None.")
    maximum = float(maximum_time_ps)
    if not np.isfinite(maximum) or maximum < 0.0:
        raise ValueError("maximum_time_ps must be finite and nonnegative.")
    tolerance = 32.0 * np.finfo(np.float64).eps * max(
        1.0, abs(maximum), abs(float(lag_times[-1]))
    )
    return max(1, int(np.searchsorted(lag_times, maximum + tolerance, side="right")))


def _project_vacf(
    vacf: VACFResult,
    subspace: AnalysisSubspace,
    stop: int,
) -> FloatArray:
    projected_sum = project_trace_from_result(
        components=vacf.components_sum[:stop],
        tensor=None if vacf.tensor_sum is None else vacf.tensor_sum[:stop],
        subspace=subspace,
        tensor_name="VACF tensor",
    )
    return np.asarray(projected_sum / float(vacf.weight_sum), dtype=np.float64)


def integrate_vacf_to_diffusion(
    vacf: VACFResult,
    *,
    axes: Sequence[AxisLabel] | None = None,
    projection_basis: ArrayLike | None = None,
    dimensions: Literal[1, 2, 3] | None = None,
    component: DiffusionComponent = "scalar",
    maximum_time_ps: float | None = None,
    integration: IntegrationMethod = "trapezoid",
) -> VACFDiffusionResult:
    """Integrate a projected self VACF into a running Green-Kubo curve.

    ``dimensions`` and ``component`` remain as compatibility adapters.  A full
    scalar VACF cannot be reinterpreted as 1D or 2D by changing only a divisor;
    use ``axes`` or ``projection_basis`` to define that physical subspace.
    """

    if not isinstance(vacf, VACFResult):
        raise TypeError("vacf must be a VACFResult instance.")
    if integration != "trapezoid":
        raise ValueError("integration must be 'trapezoid'.")
    subspace = resolve_subspace_with_legacy_options(
        axes=axes,
        projection_basis=projection_basis,
        component=component,
        dimensions=dimensions,
    )
    lag_times = _validate_vacf_lag_times(vacf)
    weighting = _resolve_physical_weighting(vacf)
    stop = _resolve_last_lag(lag_times, maximum_time_ps)
    accepted_times = np.array(lag_times[:stop], dtype=np.float64, copy=True)
    physical_vacf = _project_vacf(vacf, subspace, stop)
    integrand = physical_vacf / float(subspace.rank)
    running = cumulative_trapezoid_zero(integrand, accepted_times, axis=0)
    signature = None if vacf.signature is None else vacf.signature.with_subspace(subspace)

    metadata: dict[str, Any] = {
        "schema": "mdstats.vacf_diffusion_result.v2",
        "source_vacf_weighting": vacf.weighting,
        "resolved_physical_weighting": weighting,
        "selected_atom_indices": vacf.atom_indices.tolist(),
        "atom_count": int(vacf.atom_indices.size),
        "weight_sum": float(vacf.weight_sum),
        "drift_mode": vacf.drift_mode,
        "drift_atom_indices": vacf.metadata.get("drift_atom_indices"),
        "source_backend": vacf.backend,
        "source_lag_steps": vacf.lag_steps[:stop].tolist(),
        "source_n_origins": vacf.n_origins[:stop].tolist(),
        "requested_maximum_time_ps": maximum_time_ps,
        "actual_maximum_time_ps": float(accepted_times[-1]),
        "maximum_time_policy": "largest_stored_lag_not_exceeding_request",
        "projection_basis": subspace.projection_basis,
        "projection_labels": subspace.labels,
        "subspace_rank": subspace.rank,
        "normalization_divisor": float(subspace.rank),
        "integrand_units": "Å^2/ps^2",
        "running_diffusion_units": "Å^2/ps",
        "cm2_per_s_conversion": _A2_PER_PS_TO_CM2_PER_S,
        "green_kubo_references": (
            "Green 1954, DOI:10.1063/1.1740082",
            "Kubo 1957, DOI:10.1143/JPSJ.12.570",
        ),
        "quadrature": "cumulative composite trapezoid",
        "plateau_selected": False,
        "last_value_is_not_automatically_converged": True,
        "source_vacf_metadata": vacf.metadata,
        "signature_complete": signature is not None,
    }
    return VACFDiffusionResult(
        lag_times=accepted_times,
        running_diffusion_a2_per_ps=running,
        integrand=integrand,
        dimensions=subspace.rank,
        component=subspace.component_label,
        weighting=weighting,
        integration=integration,
        metadata=metadata,
        projection_basis=subspace.projection_basis,
        projection_labels=subspace.labels,
        signature=signature,
    )


def reconstruct_msd_from_vacf(
    vacf: VACFResult,
    *,
    axes: Sequence[AxisLabel] | None = None,
    projection_basis: ArrayLike | None = None,
    component: DiffusionComponent = "scalar",
    maximum_time_ps: float | None = None,
    integration: IntegrationMethod = "trapezoid",
) -> VACFMSDResult:
    """Reconstruct the projected MSD implied by a stored physical self VACF."""

    if not isinstance(vacf, VACFResult):
        raise TypeError("vacf must be a VACFResult instance.")
    if integration != "trapezoid":
        raise ValueError("integration must be 'trapezoid'.")
    subspace = resolve_subspace_with_legacy_options(
        axes=axes,
        projection_basis=projection_basis,
        component=component,
        dimensions=None,
    )
    lag_times = _validate_vacf_lag_times(vacf)
    weighting = _resolve_physical_weighting(vacf)
    stop = _resolve_last_lag(lag_times, maximum_time_ps)
    accepted_times = np.array(lag_times[:stop], dtype=np.float64, copy=True)
    physical_vacf = _project_vacf(vacf, subspace, stop)
    i0 = cumulative_trapezoid_zero(physical_vacf, accepted_times, axis=0)
    i1 = cumulative_trapezoid_zero(
        accepted_times * physical_vacf,
        accepted_times,
        axis=0,
    )
    reconstructed = 2.0 * (accepted_times * i0 - i1)
    reconstructed[0] = 0.0
    signature = None if vacf.signature is None else vacf.signature.with_subspace(subspace)

    metadata: dict[str, Any] = {
        "schema": "mdstats.vacf_msd_result.v2",
        "source_vacf_weighting": vacf.weighting,
        "resolved_physical_weighting": weighting,
        "selected_atom_indices": vacf.atom_indices.tolist(),
        "drift_mode": vacf.drift_mode,
        "drift_atom_indices": vacf.metadata.get("drift_atom_indices"),
        "projection_basis": subspace.projection_basis,
        "projection_labels": subspace.labels,
        "subspace_rank": subspace.rank,
        "requested_maximum_time_ps": maximum_time_ps,
        "actual_maximum_time_ps": float(accepted_times[-1]),
        "component": subspace.component_label,
        "physical_vacf_units": "Å^2/ps^2",
        "cumulative_vacf_units": "Å^2/ps",
        "cumulative_time_weighted_vacf_units": "Å^2",
        "reconstructed_msd_units": "Å^2",
        "relation": "MSD_B(t)=2*[t*I0(t)-I1(t)]",
        "transport_references": (
            "Green 1954, DOI:10.1063/1.1740082",
            "Kubo 1957, DOI:10.1143/JPSJ.12.570",
            "Helfand 1960, DOI:10.1103/PhysRev.119.1",
        ),
        "source_vacf_metadata": vacf.metadata,
        "direct_position_msd_is_primary": True,
        "finite_record_agreement_is_not_forced": True,
        "signature_complete": signature is not None,
    }
    return VACFMSDResult(
        lag_times=accepted_times,
        reconstructed_msd_a2=reconstructed,
        physical_vacf_a2_per_ps2=physical_vacf,
        cumulative_vacf_a2_per_ps=i0,
        cumulative_time_weighted_vacf_a2=i1,
        component=subspace.component_label,
        weighting=weighting,
        integration=integration,
        metadata=metadata,
        dimensions=subspace.rank,
        projection_basis=subspace.projection_basis,
        projection_labels=subspace.labels,
        signature=signature,
    )
