"""Green-Kubo ionic conductivity and Nernst-Einstein comparison.

The collective conductivity relation follows Green (J. Chem. Phys. 22,
398-413, 1954, DOI 10.1063/1.1740082) and Kubo (J. Phys. Soc. Jpn. 12,
570-586, 1957, DOI 10.1143/JPSJ.12.570).  The independent-particle
Nernst-Einstein estimate combines the Einstein self-diffusion relation with
charge transport.  Composite cumulative trapezoidal quadrature is delegated to
the package's validated SciPy-backed primitive.

C2 is deliberately restricted to fixed-cell, fully periodic, isotropic 3D
provenance.  Interval selection, compatibility checks, SI conversion auditing,
ratio policy, and immutable result schemas are mdstats design decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.constants import Boltzmann, elementary_charge

from ._dynamics_common import (
    DynamicsInputSignature,
    freeze_mapping,
    owned_readonly_array,
    require_finite_real,
    require_positive_int,
    resolve_analysis_subspace,
)
from ._quadrature import cumulative_trapezoid_zero
from .current_correlation import (
    CurrentCorrelationResult,
    _CELL_ATOL,
    _CELL_RTOL,
    _normalize_group_mapping,
)
from .diffusion import DiffusionEstimate

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

_C2_CONTRACT_VERSION = "ionic-conductivity-contract-v1"
_CONDUCTIVITY_UNITS = "S/m"
_CORRELATION_UNITS = "e^2*Angstrom^2/ps^2"
_INTEGRAL_UNITS = "e^2*Angstrom^2/ps"
# e^2 * (A^2/ps -> m^2/s) / (A^3 -> m^3) / k_B.
# (1e-8) / (1e-30) = 1e22.
_SI_NUMERATOR = float(elementary_charge**2 * 1.0e22 / Boltzmann)
_RESULT_RTOL = 5.0e-12
_RESULT_ATOL = 5.0e-13


def _as_integer_array(value: ArrayLike, *, name: str) -> IntArray:
    raw = np.asarray(value)
    if raw.ndim == 0 or np.issubdtype(raw.dtype, np.bool_) or not np.issubdtype(
        raw.dtype, np.integer
    ):
        raise TypeError(f"{name} must contain integers.")
    return np.asarray(raw, dtype=np.int64)


def _full_3d_signature(signature: DynamicsInputSignature) -> bool:
    return signature.subspace.same_physical_subspace(resolve_analysis_subspace())


def _resolve_last_lag(lag_times: FloatArray, maximum_time_ps: float | None) -> int:
    if maximum_time_ps is None:
        return int(lag_times.size)
    maximum = require_finite_real(
        maximum_time_ps,
        name="maximum_time_ps",
        nonnegative=True,
    )
    tolerance = 32.0 * np.finfo(np.float64).eps * max(
        1.0,
        abs(maximum),
        abs(float(lag_times[-1])),
    )
    if maximum > float(lag_times[-1]) + tolerance:
        raise ValueError(
            "maximum_time_ps lies beyond the largest stored correlation lag."
        )
    return max(1, int(np.searchsorted(lag_times, maximum + tolerance, side="right")))


def _resolve_fixed_volume(
    correlation: CurrentCorrelationResult,
    volume_a3: float | None,
) -> tuple[float, bool]:
    if correlation.cell_mode != "fixed" or correlation.fixed_volume_a3 is None:
        raise ValueError(
            "Ionic conductivity integration requires fixed full-cell-matrix provenance."
        )
    if not np.all(np.asarray(correlation.pbc, dtype=np.bool_)):
        raise ValueError(
            "Three-dimensional isotropic ionic conductivity requires periodicity "
            "along all three Cartesian lattice directions."
        )
    stored = require_finite_real(
        correlation.fixed_volume_a3,
        name="correlation.fixed_volume_a3",
        positive=True,
    )
    if volume_a3 is None:
        return stored, False
    asserted = require_finite_real(volume_a3, name="volume_a3", positive=True)
    if not np.isclose(asserted, stored, rtol=_CELL_RTOL, atol=_CELL_ATOL):
        raise ValueError(
            f"volume_a3={asserted:.16g} is inconsistent with stored fixed volume "
            f"{stored:.16g} Angstrom^3."
        )
    return stored, True


def _conductivity_prefactor(*, temperature_k: float, volume_a3: float) -> float:
    return _SI_NUMERATOR / (3.0 * temperature_k * volume_a3)


def _ne_prefactor(*, temperature_k: float, volume_a3: float) -> float:
    return _SI_NUMERATOR / (temperature_k * volume_a3)


@dataclass(frozen=True, slots=True)
class IonicConductivityResult:
    """Immutable running three-dimensional Green-Kubo conductivity."""

    lag_steps: IntArray
    lag_times: FloatArray
    scalar_correlation_e2_a2_per_ps2: FloatArray
    integrated_correlation_e2_a2_per_ps: FloatArray
    running_conductivity_s_per_m: FloatArray
    group_names: tuple[str, ...]
    group_scalar_correlation_e2_a2_per_ps2: FloatArray | None
    group_integrated_correlation_e2_a2_per_ps: FloatArray | None
    group_running_conductivity_s_per_m: FloatArray | None
    temperature_k: float
    volume_a3: float
    conductivity_prefactor: float
    pbc: BoolArray
    cell_mode: str
    fixed_volume_a3: float
    total_charge_e: float
    neutrality_tolerance_e: float
    charges_e: FloatArray
    current_atom_indices: IntArray
    group_atom_indices: Mapping[str, IntArray]
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lags = _as_integer_array(self.lag_steps, name="lag_steps")
        times = np.asarray(self.lag_times, dtype=np.float64)
        correlation = np.asarray(
            self.scalar_correlation_e2_a2_per_ps2,
            dtype=np.float64,
        )
        integrated = np.asarray(
            self.integrated_correlation_e2_a2_per_ps,
            dtype=np.float64,
        )
        running = np.asarray(self.running_conductivity_s_per_m, dtype=np.float64)
        names = tuple(self.group_names)
        group_scalar = (
            None
            if self.group_scalar_correlation_e2_a2_per_ps2 is None
            else np.asarray(
                self.group_scalar_correlation_e2_a2_per_ps2,
                dtype=np.float64,
            )
        )
        group_integrated = (
            None
            if self.group_integrated_correlation_e2_a2_per_ps is None
            else np.asarray(
                self.group_integrated_correlation_e2_a2_per_ps,
                dtype=np.float64,
            )
        )
        group_running = (
            None
            if self.group_running_conductivity_s_per_m is None
            else np.asarray(self.group_running_conductivity_s_per_m, dtype=np.float64)
        )
        charges = np.asarray(self.charges_e, dtype=np.float64)
        current_indices = _as_integer_array(
            self.current_atom_indices,
            name="current_atom_indices",
        )

        if lags.ndim != 1 or lags.size < 1 or np.any(lags < 0):
            raise ValueError("lag_steps must be nonempty, one-dimensional, and nonnegative.")
        if lags.size > 1 and np.any(np.diff(lags) <= 0):
            raise ValueError("lag_steps must be strictly increasing.")
        n_lags = int(lags.size)
        for name, value in (
            ("lag_times", times),
            ("scalar_correlation_e2_a2_per_ps2", correlation),
            ("integrated_correlation_e2_a2_per_ps", integrated),
            ("running_conductivity_s_per_m", running),
        ):
            if value.shape != (n_lags,) or not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must be finite with shape (L,).")
        if not np.isclose(times[0], 0.0, rtol=0.0, atol=1.0e-14):
            raise ValueError("lag_times must start at zero.")
        if times.size > 1 and np.any(np.diff(times) <= 0.0):
            raise ValueError("lag_times must be strictly increasing.")
        if not np.isclose(integrated[0], 0.0, rtol=0.0, atol=1.0e-14):
            raise ValueError("integrated correlation must start at zero.")
        if not np.isclose(running[0], 0.0, rtol=0.0, atol=1.0e-14):
            raise ValueError("running conductivity must start at zero.")

        temperature = require_finite_real(
            self.temperature_k,
            name="temperature_k",
            positive=True,
        )
        volume = require_finite_real(self.volume_a3, name="volume_a3", positive=True)
        prefactor = require_finite_real(
            self.conductivity_prefactor,
            name="conductivity_prefactor",
            positive=True,
        )
        expected_prefactor = _conductivity_prefactor(
            temperature_k=temperature,
            volume_a3=volume,
        )
        if not np.isclose(prefactor, expected_prefactor, rtol=2.0e-15, atol=0.0):
            raise ValueError("conductivity_prefactor is inconsistent with T and V.")
        pbc = np.asarray(self.pbc, dtype=np.bool_)
        if pbc.shape != (3,) or not np.all(pbc):
            raise ValueError("Ionic conductivity requires full three-dimensional periodicity.")
        if self.cell_mode != "fixed":
            raise ValueError("Ionic conductivity requires cell_mode='fixed'.")
        fixed_volume = require_finite_real(
            self.fixed_volume_a3,
            name="fixed_volume_a3",
            positive=True,
        )
        if not np.isclose(fixed_volume, volume, rtol=_CELL_RTOL, atol=_CELL_ATOL):
            raise ValueError("fixed_volume_a3 is inconsistent with volume_a3.")
        total_charge = require_finite_real(self.total_charge_e, name="total_charge_e")
        neutrality_tolerance = require_finite_real(
            self.neutrality_tolerance_e,
            name="neutrality_tolerance_e",
            nonnegative=True,
        )
        expected_integrated = cumulative_trapezoid_zero(correlation, times, axis=0)
        if not np.allclose(
            integrated,
            expected_integrated,
            rtol=_RESULT_RTOL,
            atol=_RESULT_ATOL,
        ):
            raise ValueError("integrated correlation is inconsistent with trapezoidal quadrature.")
        if not np.allclose(
            running,
            integrated * prefactor,
            rtol=_RESULT_RTOL,
            atol=_RESULT_ATOL,
        ):
            raise ValueError("running conductivity is inconsistent with SI conversion.")

        if charges.ndim != 1 or charges.size < 1 or not np.all(np.isfinite(charges)):
            raise ValueError("charges_e must be finite and one-dimensional.")
        expected_current = np.flatnonzero(charges != 0.0).astype(np.int64)
        if not np.array_equal(current_indices, expected_current):
            raise ValueError("current_atom_indices is inconsistent with charges_e.")
        expected_total_charge = float(np.sum(charges, dtype=np.float64))
        if not np.isclose(
            total_charge,
            expected_total_charge,
            rtol=0.0,
            atol=max(1.0e-15, 10.0 * np.finfo(np.float64).eps * max(1.0, float(np.sum(np.abs(charges))))),
        ) or abs(total_charge) > neutrality_tolerance:
            raise ValueError("Charge provenance is inconsistent or non-neutral.")
        groups = (
            _normalize_group_mapping(
                self.group_atom_indices,
                group_names=names,
                n_atoms=int(charges.size),
                current_atom_indices=current_indices,
            )
            if names
            else freeze_mapping({})
        )
        if names:
            expected_shape = (n_lags, len(names), len(names))
            if group_scalar is None or group_scalar.shape != expected_shape:
                raise ValueError(
                    "group_scalar_correlation_e2_a2_per_ps2 must have shape (L, G, G)."
                )
            if not np.all(np.isfinite(group_scalar)):
                raise ValueError("Group scalar correlations must contain only finite values.")
            if not np.allclose(
                correlation,
                np.sum(group_scalar, axis=(1, 2)),
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Ordered group correlations must sum to total correlation.")
            if group_integrated is None or group_integrated.shape != expected_shape:
                raise ValueError(
                    "group_integrated_correlation_e2_a2_per_ps must have shape (L, G, G)."
                )
            if group_running is None or group_running.shape != expected_shape:
                raise ValueError(
                    "group_running_conductivity_s_per_m must have shape (L, G, G)."
                )
            if not np.all(np.isfinite(group_integrated)) or not np.all(
                np.isfinite(group_running)
            ):
                raise ValueError("Group conductivity arrays must contain only finite values.")
            expected_group_integrated = cumulative_trapezoid_zero(
                group_scalar,
                times,
                axis=0,
            )
            if not np.allclose(
                group_integrated,
                expected_group_integrated,
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Group integrated correlations are inconsistent with quadrature.")
            if not np.allclose(
                group_running,
                group_integrated * prefactor,
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Group running conductivity is inconsistent with SI conversion.")
            if not np.allclose(
                integrated,
                np.sum(group_integrated, axis=(1, 2)),
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Ordered group integrals must sum to the total integral.")
            if not np.allclose(
                running,
                np.sum(group_running, axis=(1, 2)),
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Ordered group conductivities must sum to total conductivity.")
        else:
            if group_scalar is not None or group_integrated is not None or group_running is not None:
                raise ValueError("Group arrays must be None when no current groups exist.")
            if len(self.group_atom_indices) != 0:
                raise ValueError("group_atom_indices must be empty when no groups exist.")

        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not _full_3d_signature(self.signature):
            raise ValueError("Ionic conductivity requires the full 3D physical subspace.")
        if not np.array_equal(self.signature.atom_indices, current_indices):
            raise ValueError("signature atom indices are inconsistent with current atoms.")
        spacing = self.signature.sample_spacing_ps
        if spacing is None or not np.allclose(
            times,
            lags.astype(np.float64) * spacing,
            rtol=1.0e-12,
            atol=1.0e-14,
        ):
            raise ValueError("lag_times is inconsistent with lag steps and signature spacing.")

        object.__setattr__(self, "lag_steps", owned_readonly_array(lags, dtype=np.int64))
        object.__setattr__(self, "lag_times", owned_readonly_array(times, dtype=np.float64))
        object.__setattr__(
            self,
            "scalar_correlation_e2_a2_per_ps2",
            owned_readonly_array(correlation, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "integrated_correlation_e2_a2_per_ps",
            owned_readonly_array(integrated, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "running_conductivity_s_per_m",
            owned_readonly_array(running, dtype=np.float64),
        )
        object.__setattr__(self, "group_names", names)
        object.__setattr__(
            self,
            "group_scalar_correlation_e2_a2_per_ps2",
            None
            if group_scalar is None
            else owned_readonly_array(group_scalar, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "group_integrated_correlation_e2_a2_per_ps",
            None
            if group_integrated is None
            else owned_readonly_array(group_integrated, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "group_running_conductivity_s_per_m",
            None
            if group_running is None
            else owned_readonly_array(group_running, dtype=np.float64),
        )
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "volume_a3", volume)
        object.__setattr__(self, "conductivity_prefactor", prefactor)
        object.__setattr__(self, "pbc", owned_readonly_array(pbc, dtype=np.bool_))
        object.__setattr__(self, "cell_mode", "fixed")
        object.__setattr__(self, "fixed_volume_a3", fixed_volume)
        object.__setattr__(self, "total_charge_e", total_charge)
        object.__setattr__(self, "neutrality_tolerance_e", neutrality_tolerance)
        object.__setattr__(self, "charges_e", owned_readonly_array(charges, dtype=np.float64))
        object.__setattr__(
            self,
            "current_atom_indices",
            owned_readonly_array(current_indices, dtype=np.int64),
        )
        object.__setattr__(self, "group_atom_indices", groups)
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class IonicConductivityEstimate:
    """Explicit interval estimate from a running ionic conductivity curve."""

    value_s_per_m: float
    standard_error_s_per_m: float | None
    time_range_ps: tuple[float, float]
    method: str
    n_points: int
    is_stable: bool | None
    diagnostics: Mapping[str, Any]
    group_names: tuple[str, ...]
    group_pair_values_s_per_m: FloatArray | None
    temperature_k: float
    volume_a3: float
    pbc: BoolArray
    cell_mode: str
    fixed_volume_a3: float
    total_charge_e: float
    neutrality_tolerance_e: float
    charges_e: FloatArray
    current_atom_indices: IntArray
    group_atom_indices: Mapping[str, IntArray]
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        value = require_finite_real(self.value_s_per_m, name="value_s_per_m")
        standard_error = (
            None
            if self.standard_error_s_per_m is None
            else require_finite_real(
                self.standard_error_s_per_m,
                name="standard_error_s_per_m",
                nonnegative=True,
            )
        )
        if not isinstance(self.time_range_ps, tuple) or len(self.time_range_ps) != 2:
            raise TypeError("time_range_ps must be a two-element tuple.")
        start = require_finite_real(self.time_range_ps[0], name="time_range_ps[0]")
        end = require_finite_real(self.time_range_ps[1], name="time_range_ps[1]")
        if end <= start:
            raise ValueError("time_range_ps must satisfy end > start.")
        if self.method != "explicit":
            raise ValueError("Only method='explicit' is supported.")
        n_points = require_positive_int(self.n_points, name="n_points")
        if n_points < 2:
            raise ValueError("n_points must be at least two.")
        if self.is_stable is not None and not isinstance(
            self.is_stable,
            (bool, np.bool_),
        ):
            raise TypeError("is_stable must be bool or None.")
        temperature = require_finite_real(
            self.temperature_k,
            name="temperature_k",
            positive=True,
        )
        volume = require_finite_real(self.volume_a3, name="volume_a3", positive=True)
        pbc = np.asarray(self.pbc, dtype=np.bool_)
        if pbc.shape != (3,) or not np.all(pbc):
            raise ValueError("Ionic conductivity estimates require full periodicity.")
        if self.cell_mode != "fixed":
            raise ValueError("Ionic conductivity estimates require cell_mode='fixed'.")
        fixed_volume = require_finite_real(
            self.fixed_volume_a3,
            name="fixed_volume_a3",
            positive=True,
        )
        if not np.isclose(fixed_volume, volume, rtol=_CELL_RTOL, atol=_CELL_ATOL):
            raise ValueError("fixed_volume_a3 is inconsistent with volume_a3.")
        total_charge = require_finite_real(self.total_charge_e, name="total_charge_e")
        neutrality_tolerance = require_finite_real(
            self.neutrality_tolerance_e,
            name="neutrality_tolerance_e",
            nonnegative=True,
        )
        names = tuple(self.group_names)
        charges = np.asarray(self.charges_e, dtype=np.float64)
        current_indices = _as_integer_array(
            self.current_atom_indices,
            name="current_atom_indices",
        )
        if charges.ndim != 1 or charges.size < 1 or not np.all(np.isfinite(charges)):
            raise ValueError("charges_e must be finite and one-dimensional.")
        expected_current = np.flatnonzero(charges != 0.0).astype(np.int64)
        if not np.array_equal(current_indices, expected_current):
            raise ValueError("current_atom_indices is inconsistent with charges_e.")
        expected_total_charge = float(np.sum(charges, dtype=np.float64))
        if not np.isclose(
            total_charge,
            expected_total_charge,
            rtol=0.0,
            atol=max(1.0e-15, 10.0 * np.finfo(np.float64).eps * max(1.0, float(np.sum(np.abs(charges))))),
        ) or abs(total_charge) > neutrality_tolerance:
            raise ValueError("Charge provenance is inconsistent or non-neutral.")
        groups = (
            _normalize_group_mapping(
                self.group_atom_indices,
                group_names=names,
                n_atoms=int(charges.size),
                current_atom_indices=current_indices,
            )
            if names
            else freeze_mapping({})
        )
        group_values = (
            None
            if self.group_pair_values_s_per_m is None
            else np.asarray(self.group_pair_values_s_per_m, dtype=np.float64)
        )
        if names:
            expected_shape = (len(names), len(names))
            if group_values is None or group_values.shape != expected_shape:
                raise ValueError("group_pair_values_s_per_m must have shape (G, G).")
            if not np.all(np.isfinite(group_values)):
                raise ValueError("group_pair_values_s_per_m must be finite.")
            if not np.isclose(
                value,
                float(np.sum(group_values)),
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("Ordered group-pair estimates must sum to total conductivity.")
        elif group_values is not None or len(self.group_atom_indices) != 0:
            raise ValueError("Group estimate fields must be absent when no groups exist.")
        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not _full_3d_signature(self.signature):
            raise ValueError("Ionic conductivity estimates require the full 3D subspace.")
        if not np.array_equal(self.signature.atom_indices, current_indices):
            raise ValueError("signature atom indices are inconsistent with current atoms.")

        object.__setattr__(self, "value_s_per_m", value)
        object.__setattr__(self, "standard_error_s_per_m", standard_error)
        object.__setattr__(self, "time_range_ps", (start, end))
        object.__setattr__(self, "n_points", n_points)
        object.__setattr__(
            self,
            "is_stable",
            None if self.is_stable is None else bool(self.is_stable),
        )
        object.__setattr__(self, "diagnostics", freeze_mapping(self.diagnostics))
        object.__setattr__(self, "group_names", names)
        object.__setattr__(
            self,
            "group_pair_values_s_per_m",
            None
            if group_values is None
            else owned_readonly_array(group_values, dtype=np.float64),
        )
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "volume_a3", volume)
        object.__setattr__(self, "pbc", owned_readonly_array(pbc, dtype=np.bool_))
        object.__setattr__(self, "cell_mode", "fixed")
        object.__setattr__(self, "fixed_volume_a3", fixed_volume)
        object.__setattr__(self, "total_charge_e", total_charge)
        object.__setattr__(self, "neutrality_tolerance_e", neutrality_tolerance)
        object.__setattr__(self, "charges_e", owned_readonly_array(charges, dtype=np.float64))
        object.__setattr__(
            self,
            "current_atom_indices",
            owned_readonly_array(current_indices, dtype=np.int64),
        )
        object.__setattr__(self, "group_atom_indices", groups)
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class NernstEinsteinComparisonResult:
    """Collective Green-Kubo and independent-particle conductivity comparison."""

    collective_conductivity_s_per_m: float
    nernst_einstein_conductivity_s_per_m: float
    signed_difference_s_per_m: float
    absolute_difference_s_per_m: float
    collective_over_nernst_einstein: float
    nernst_einstein_over_collective: float
    collective_over_nernst_einstein_defined: bool
    nernst_einstein_over_collective_defined: bool
    group_names: tuple[str, ...]
    species_counts: IntArray
    group_charges_e: FloatArray
    diffusion_a2_per_ps: FloatArray
    species_contributions_s_per_m: FloatArray
    off_diagonal_group_contribution_s_per_m: float
    temperature_k: float
    volume_a3: float
    conductivity_time_range_ps: tuple[float, float]
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        collective = require_finite_real(
            self.collective_conductivity_s_per_m,
            name="collective_conductivity_s_per_m",
        )
        ne_value = require_finite_real(
            self.nernst_einstein_conductivity_s_per_m,
            name="nernst_einstein_conductivity_s_per_m",
            nonnegative=True,
        )
        signed = require_finite_real(
            self.signed_difference_s_per_m,
            name="signed_difference_s_per_m",
        )
        absolute = require_finite_real(
            self.absolute_difference_s_per_m,
            name="absolute_difference_s_per_m",
            nonnegative=True,
        )
        if not np.isclose(signed, collective - ne_value, rtol=_RESULT_RTOL, atol=_RESULT_ATOL):
            raise ValueError("signed_difference_s_per_m is inconsistent.")
        if not np.isclose(absolute, abs(signed), rtol=_RESULT_RTOL, atol=_RESULT_ATOL):
            raise ValueError("absolute_difference_s_per_m is inconsistent.")

        if not isinstance(self.collective_over_nernst_einstein_defined, (bool, np.bool_)):
            raise TypeError("collective_over_nernst_einstein_defined must be bool.")
        if not isinstance(self.nernst_einstein_over_collective_defined, (bool, np.bool_)):
            raise TypeError("nernst_einstein_over_collective_defined must be bool.")
        c_over_ne_defined = bool(self.collective_over_nernst_einstein_defined)
        ne_over_c_defined = bool(self.nernst_einstein_over_collective_defined)
        c_over_ne = float(self.collective_over_nernst_einstein)
        ne_over_c = float(self.nernst_einstein_over_collective)
        expected_c_over_ne_defined = ne_value != 0.0
        expected_ne_over_c_defined = collective != 0.0
        if c_over_ne_defined != expected_c_over_ne_defined:
            raise ValueError("collective/NE ratio-defined flag is inconsistent.")
        if ne_over_c_defined != expected_ne_over_c_defined:
            raise ValueError("NE/collective ratio-defined flag is inconsistent.")
        if c_over_ne_defined:
            if not np.isfinite(c_over_ne) or not np.isclose(
                c_over_ne,
                collective / ne_value,
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("collective_over_nernst_einstein is inconsistent.")
        elif not np.isnan(c_over_ne):
            raise ValueError("Undefined collective/NE ratio must be NaN.")
        if ne_over_c_defined:
            if not np.isfinite(ne_over_c) or not np.isclose(
                ne_over_c,
                ne_value / collective,
                rtol=_RESULT_RTOL,
                atol=_RESULT_ATOL,
            ):
                raise ValueError("nernst_einstein_over_collective is inconsistent.")
        elif not np.isnan(ne_over_c):
            raise ValueError("Undefined NE/collective ratio must be NaN.")

        names = tuple(self.group_names)
        counts = _as_integer_array(self.species_counts, name="species_counts")
        charges = np.asarray(self.group_charges_e, dtype=np.float64)
        diffusion = np.asarray(self.diffusion_a2_per_ps, dtype=np.float64)
        contributions = np.asarray(self.species_contributions_s_per_m, dtype=np.float64)
        n_groups = len(names)
        if n_groups < 1 or len(set(names)) != n_groups or any(not name for name in names):
            raise ValueError("group_names must contain unique nonempty names.")
        for name, value in (
            ("species_counts", counts),
            ("group_charges_e", charges),
            ("diffusion_a2_per_ps", diffusion),
            ("species_contributions_s_per_m", contributions),
        ):
            if value.shape != (n_groups,):
                raise ValueError(f"{name} must have shape (G,).")
        if np.any(counts < 1):
            raise ValueError("species_counts must be positive.")
        if not np.all(np.isfinite(charges)) or np.any(charges == 0.0):
            raise ValueError("group_charges_e must be finite and nonzero.")
        if not np.all(np.isfinite(diffusion)) or np.any(diffusion < 0.0):
            raise ValueError("diffusion_a2_per_ps must be finite and nonnegative.")
        if not np.all(np.isfinite(contributions)) or np.any(contributions < 0.0):
            raise ValueError("species_contributions_s_per_m must be finite and nonnegative.")
        if not np.isclose(
            ne_value,
            float(np.sum(contributions)),
            rtol=_RESULT_RTOL,
            atol=_RESULT_ATOL,
        ):
            raise ValueError("Species contributions must sum to NE conductivity.")

        off_diagonal = require_finite_real(
            self.off_diagonal_group_contribution_s_per_m,
            name="off_diagonal_group_contribution_s_per_m",
        )
        temperature = require_finite_real(
            self.temperature_k,
            name="temperature_k",
            positive=True,
        )
        volume = require_finite_real(self.volume_a3, name="volume_a3", positive=True)
        if not isinstance(self.conductivity_time_range_ps, tuple) or len(
            self.conductivity_time_range_ps
        ) != 2:
            raise TypeError("conductivity_time_range_ps must be a two-element tuple.")
        start = require_finite_real(
            self.conductivity_time_range_ps[0],
            name="conductivity_time_range_ps[0]",
        )
        end = require_finite_real(
            self.conductivity_time_range_ps[1],
            name="conductivity_time_range_ps[1]",
        )
        if end <= start:
            raise ValueError("conductivity_time_range_ps must satisfy end > start.")
        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not _full_3d_signature(self.signature):
            raise ValueError("Nernst-Einstein comparison requires the full 3D subspace.")

        object.__setattr__(self, "collective_conductivity_s_per_m", collective)
        object.__setattr__(self, "nernst_einstein_conductivity_s_per_m", ne_value)
        object.__setattr__(self, "signed_difference_s_per_m", signed)
        object.__setattr__(self, "absolute_difference_s_per_m", absolute)
        object.__setattr__(self, "collective_over_nernst_einstein", c_over_ne)
        object.__setattr__(self, "nernst_einstein_over_collective", ne_over_c)
        object.__setattr__(
            self,
            "collective_over_nernst_einstein_defined",
            c_over_ne_defined,
        )
        object.__setattr__(
            self,
            "nernst_einstein_over_collective_defined",
            ne_over_c_defined,
        )
        object.__setattr__(self, "group_names", names)
        object.__setattr__(self, "species_counts", owned_readonly_array(counts, dtype=np.int64))
        object.__setattr__(self, "group_charges_e", owned_readonly_array(charges, dtype=np.float64))
        object.__setattr__(self, "diffusion_a2_per_ps", owned_readonly_array(diffusion, dtype=np.float64))
        object.__setattr__(
            self,
            "species_contributions_s_per_m",
            owned_readonly_array(contributions, dtype=np.float64),
        )
        object.__setattr__(self, "off_diagonal_group_contribution_s_per_m", off_diagonal)
        object.__setattr__(self, "temperature_k", temperature)
        object.__setattr__(self, "volume_a3", volume)
        object.__setattr__(self, "conductivity_time_range_ps", (start, end))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))


def integrate_ionic_conductivity(
    correlation: CurrentCorrelationResult,
    *,
    temperature_k: float,
    volume_a3: float | None = None,
    maximum_time_ps: float | None = None,
) -> IonicConductivityResult:
    """Integrate a fixed-volume collective current correlation into SI conductivity."""

    if not isinstance(correlation, CurrentCorrelationResult):
        raise TypeError("correlation must be a CurrentCorrelationResult.")
    temperature = require_finite_real(
        temperature_k,
        name="temperature_k",
        positive=True,
    )
    if not _full_3d_signature(correlation.signature):
        raise ValueError("Ionic conductivity requires the full 3D physical subspace.")
    volume, volume_asserted = _resolve_fixed_volume(correlation, volume_a3)
    times_all = np.asarray(correlation.lag_times, dtype=np.float64)
    stop = _resolve_last_lag(times_all, maximum_time_ps)
    lags = np.asarray(correlation.lag_steps[:stop], dtype=np.int64)
    times = times_all[:stop]
    scalar = np.asarray(correlation.scalar[:stop], dtype=np.float64)
    integrated = cumulative_trapezoid_zero(scalar, times, axis=0)
    prefactor = _conductivity_prefactor(temperature_k=temperature, volume_a3=volume)
    running = integrated * prefactor

    group_scalar: FloatArray | None = None
    group_integrated: FloatArray | None = None
    group_running: FloatArray | None = None
    if correlation.group_scalar is not None:
        group_scalar = np.asarray(correlation.group_scalar[:stop], dtype=np.float64)
        group_integrated = cumulative_trapezoid_zero(group_scalar, times, axis=0)
        group_running = group_integrated * prefactor

    metadata: dict[str, Any] = {
        "contract_version": _C2_CONTRACT_VERSION,
        "source_correlation_contract_version": correlation.metadata.get(
            "contract_version"
        ),
        "source_backend": correlation.backend,
        "correlation_units": _CORRELATION_UNITS,
        "integrated_correlation_units": _INTEGRAL_UNITS,
        "conductivity_units": _CONDUCTIVITY_UNITS,
        "integration": "trapezoid",
        "isotropic_dimensions": 3,
        "temperature_k": temperature,
        "volume_a3": volume,
        "volume_argument_was_asserted": volume_asserted,
        "maximum_time_ps": maximum_time_ps,
        "retained_lag_count": int(stop),
        "elementary_charge_c": float(elementary_charge),
        "boltzmann_j_per_k": float(Boltzmann),
        "angstrom2_per_ps_to_m2_per_s": 1.0e-8,
        "angstrom3_to_m3": 1.0e-30,
        "si_numerator_e2_1e22_over_kb": _SI_NUMERATOR,
        "conductivity_prefactor": prefactor,
        "ordered_group_contributions": bool(correlation.group_names),
        "source_correlation_metadata": correlation.metadata,
    }
    return IonicConductivityResult(
        lag_steps=lags,
        lag_times=times,
        scalar_correlation_e2_a2_per_ps2=scalar,
        integrated_correlation_e2_a2_per_ps=integrated,
        running_conductivity_s_per_m=running,
        group_names=correlation.group_names,
        group_scalar_correlation_e2_a2_per_ps2=group_scalar,
        group_integrated_correlation_e2_a2_per_ps=group_integrated,
        group_running_conductivity_s_per_m=group_running,
        temperature_k=temperature,
        volume_a3=volume,
        conductivity_prefactor=prefactor,
        pbc=correlation.pbc,
        cell_mode=correlation.cell_mode,
        fixed_volume_a3=volume,
        total_charge_e=correlation.total_charge_e,
        neutrality_tolerance_e=correlation.neutrality_tolerance_e,
        charges_e=correlation.charges_e,
        current_atom_indices=correlation.current_atom_indices,
        group_atom_indices=correlation.group_atom_indices,
        signature=correlation.signature,
        metadata=metadata,
    )


def _validate_interval(
    time_range_ps: tuple[float, float],
    *,
    available_start: float,
    available_end: float,
) -> tuple[float, float]:
    if not isinstance(time_range_ps, tuple) or len(time_range_ps) != 2:
        raise TypeError("time_range_ps must be a two-element tuple.")
    start = require_finite_real(time_range_ps[0], name="time_range_ps[0]")
    end = require_finite_real(time_range_ps[1], name="time_range_ps[1]")
    if end <= start:
        raise ValueError("time_range_ps must satisfy end > start.")
    tolerance = 64.0 * np.finfo(np.float64).eps * max(
        1.0,
        abs(available_start),
        abs(available_end),
        abs(start),
        abs(end),
    )
    if start < available_start - tolerance or end > available_end + tolerance:
        raise ValueError(
            f"time_range_ps={time_range_ps!r} lies outside the available interval "
            f"[{available_start}, {available_end}]."
        )
    return start, end


def _select_interval(times: FloatArray, interval: tuple[float, float]) -> IntArray:
    start, end = interval
    tolerance = 64.0 * np.finfo(np.float64).eps * max(
        1.0,
        abs(start),
        abs(end),
        abs(float(times[-1])),
    )
    return np.flatnonzero((times >= start - tolerance) & (times <= end + tolerance)).astype(
        np.int64
    )


def _require_uniform_grid(times: FloatArray) -> float:
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
            "The selected conductivity plateau samples must be uniformly spaced."
        )
    return float(increments[0])


def _centered_linear_diagnostics(
    x: FloatArray,
    y: FloatArray,
) -> tuple[float, float, float, float]:
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    xc = x - x_mean
    yc = y - y_mean
    denominator = float(np.dot(xc, xc))
    if denominator <= 0.0:
        raise ValueError("The selected time coordinates do not span an interval.")
    slope = float(np.dot(xc, yc) / denominator)
    intercept = float(y_mean - slope * x_mean)
    residual = y - (intercept + slope * x)
    residual_rms = float(np.sqrt(np.mean(residual * residual)))
    total = float(np.dot(yc, yc))
    r_squared = (
        1.0
        if total == 0.0 and residual_rms == 0.0
        else (0.0 if total == 0.0 else float(1.0 - np.dot(residual, residual) / total))
    )
    return slope, intercept, r_squared, residual_rms


def estimate_ionic_conductivity_plateau(
    running: IonicConductivityResult,
    *,
    time_range_ps: tuple[float, float],
    minimum_points: int = 8,
    slope_tolerance_s_per_m_ps: float | None = None,
) -> IonicConductivityEstimate:
    """Estimate conductivity over an explicit uniformly sampled running interval."""

    if not isinstance(running, IonicConductivityResult):
        raise TypeError("running must be an IonicConductivityResult.")
    minimum = require_positive_int(minimum_points, name="minimum_points")
    if minimum < 2:
        raise ValueError("minimum_points must be at least two.")
    tolerance = (
        None
        if slope_tolerance_s_per_m_ps is None
        else require_finite_real(
            slope_tolerance_s_per_m_ps,
            name="slope_tolerance_s_per_m_ps",
            nonnegative=True,
        )
    )
    times = np.asarray(running.lag_times, dtype=np.float64)
    values = np.asarray(running.running_conductivity_s_per_m, dtype=np.float64)
    requested = _validate_interval(
        time_range_ps,
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
    spacing = _require_uniform_grid(selected_times)
    slope, intercept, r_squared, residual_rms = _centered_linear_diagnostics(
        selected_times,
        selected_values,
    )
    estimate = float(np.mean(selected_values))
    group_values: FloatArray | None = None
    if running.group_running_conductivity_s_per_m is not None:
        group_values = np.mean(
            np.asarray(running.group_running_conductivity_s_per_m)[selected],
            axis=0,
        )
    stable = None if tolerance is None else bool(abs(slope) <= tolerance)
    actual_range = (float(selected_times[0]), float(selected_times[-1]))
    diagnostics: dict[str, Any] = {
        "interval_mean_s_per_m": estimate,
        "interval_median_s_per_m": float(np.median(selected_values)),
        "interval_sample_standard_deviation_s_per_m": float(
            np.std(selected_values, ddof=1)
        ),
        "interval_minimum_s_per_m": float(np.min(selected_values)),
        "interval_maximum_s_per_m": float(np.max(selected_values)),
        "interval_span_s_per_m": float(np.ptp(selected_values)),
        "endpoint_drift_s_per_m": float(selected_values[-1] - selected_values[0]),
        "linear_slope_s_per_m_ps": slope,
        "linear_intercept_s_per_m": intercept,
        "linear_r_squared": r_squared,
        "linear_residual_rms_s_per_m": residual_rms,
        "selected_sample_spacing_ps": spacing,
        "slope_tolerance_s_per_m_ps": tolerance,
        "passes_slope_tolerance": stable,
        "uncertainty_policy": (
            "no_independent_sample_standard_error_from_one_serially_correlated_"
            "running_curve"
        ),
        "automatic_plateau_search": False,
        "tail_fit": False,
    }
    metadata: dict[str, Any] = {
        "contract_version": _C2_CONTRACT_VERSION,
        "schema": "mdstats.ionic_conductivity_estimate.v1",
        "requested_time_range_ps": requested,
        "actual_time_range_ps": actual_range,
        "selected_indices": selected.tolist(),
        "source_integration": "trapezoid",
        "source_running_metadata": running.metadata,
        "conductivity_units": _CONDUCTIVITY_UNITS,
        "plateau_method_is_mdstats_design": True,
    }
    return IonicConductivityEstimate(
        value_s_per_m=estimate,
        standard_error_s_per_m=None,
        time_range_ps=actual_range,
        method="explicit",
        n_points=int(selected.size),
        is_stable=stable,
        diagnostics=diagnostics,
        group_names=running.group_names,
        group_pair_values_s_per_m=group_values,
        temperature_k=running.temperature_k,
        volume_a3=running.volume_a3,
        pbc=running.pbc,
        cell_mode=running.cell_mode,
        fixed_volume_a3=running.fixed_volume_a3,
        total_charge_e=running.total_charge_e,
        neutrality_tolerance_e=running.neutrality_tolerance_e,
        charges_e=running.charges_e,
        current_atom_indices=running.current_atom_indices,
        group_atom_indices=running.group_atom_indices,
        signature=running.signature,
        metadata=metadata,
    )


def _transport_identity_mismatches(
    current_signature: DynamicsInputSignature,
    diffusion_signature: DynamicsInputSignature,
) -> tuple[str, ...]:
    mismatches: list[str] = []
    scalar_fields = (
        "source_format",
        "source_files",
        "trajectory_fingerprint",
        "frame_indices",
        "n_frames",
        "sample_spacing_ps",
        "drift_mode",
    )
    for name in scalar_fields:
        if getattr(current_signature, name) != getattr(diffusion_signature, name):
            mismatches.append(name)
    if not np.array_equal(
        current_signature.frame_times_ps,
        diffusion_signature.frame_times_ps,
    ):
        mismatches.append("frame_times_ps")
    left_drift = current_signature.drift_atom_indices
    right_drift = diffusion_signature.drift_atom_indices
    if left_drift is None or right_drift is None:
        if left_drift is not right_drift:
            mismatches.append("drift_atom_indices")
    elif not np.array_equal(left_drift, right_drift):
        mismatches.append("drift_atom_indices")
    return tuple(mismatches)


def compute_nernst_einstein_comparison(
    conductivity: IonicConductivityEstimate,
    species_diffusion: Mapping[str, DiffusionEstimate],
    *,
    temperature_k: float | None = None,
    volume_a3: float | None = None,
) -> NernstEinsteinComparisonResult:
    """Compare collective conductivity with compatible species self diffusion."""

    if not isinstance(conductivity, IonicConductivityEstimate):
        raise TypeError("conductivity must be an IonicConductivityEstimate.")
    if not isinstance(species_diffusion, Mapping):
        raise TypeError("species_diffusion must be a mapping.")
    if not conductivity.group_names:
        raise ValueError(
            "Nernst-Einstein comparison requires a nonempty exact current-group partition."
        )
    if tuple(species_diffusion.keys()) != conductivity.group_names:
        raise ValueError(
            "species_diffusion keys and order must match conductivity.group_names exactly."
        )
    if temperature_k is not None:
        asserted_temperature = require_finite_real(
            temperature_k,
            name="temperature_k",
            positive=True,
        )
        if not np.isclose(
            asserted_temperature,
            conductivity.temperature_k,
            rtol=1.0e-12,
            atol=1.0e-12,
        ):
            raise ValueError("temperature_k is inconsistent with the conductivity estimate.")
    if volume_a3 is not None:
        asserted_volume = require_finite_real(volume_a3, name="volume_a3", positive=True)
        if not np.isclose(
            asserted_volume,
            conductivity.volume_a3,
            rtol=_CELL_RTOL,
            atol=_CELL_ATOL,
        ):
            raise ValueError("volume_a3 is inconsistent with the conductivity estimate.")

    n_groups = len(conductivity.group_names)
    counts = np.empty(n_groups, dtype=np.int64)
    group_charges = np.empty(n_groups, dtype=np.float64)
    diffusion_values = np.empty(n_groups, dtype=np.float64)
    mismatch_report: dict[str, tuple[str, ...]] = {}
    for position, name in enumerate(conductivity.group_names):
        estimate = species_diffusion[name]
        if not isinstance(estimate, DiffusionEstimate):
            raise TypeError(
                f"species_diffusion[{name!r}] must be a DiffusionEstimate."
            )
        if estimate.signature is None:
            raise ValueError(
                f"species_diffusion[{name!r}] lacks a complete dynamics signature."
            )
        if estimate.dimensions != 3 or not _full_3d_signature(estimate.signature):
            raise ValueError(
                f"species_diffusion[{name!r}] must use the full three-dimensional subspace."
            )
        group_indices = np.asarray(
            conductivity.group_atom_indices[name],
            dtype=np.int64,
        )
        if not np.array_equal(estimate.signature.atom_indices, group_indices):
            raise ValueError(
                f"species_diffusion[{name!r}] atom selection does not match the current group."
            )
        mismatches = _transport_identity_mismatches(
            conductivity.signature,
            estimate.signature,
        )
        if mismatches:
            mismatch_report[name] = mismatches
        value = require_finite_real(
            estimate.value_a2_per_ps,
            name=f"species_diffusion[{name!r}].value_a2_per_ps",
            nonnegative=True,
        )
        group_charge_values = np.asarray(conductivity.charges_e[group_indices], dtype=np.float64)
        charge = float(group_charge_values[0])
        if charge == 0.0 or not np.allclose(
            group_charge_values,
            charge,
            rtol=0.0,
            atol=1.0e-14,
        ):
            raise ValueError(
                f"Current group {name!r} must contain one uniform nonzero charge."
            )
        counts[position] = int(group_indices.size)
        group_charges[position] = charge
        diffusion_values[position] = value
    if mismatch_report:
        detail = "; ".join(
            f"{name}: {', '.join(fields)}" for name, fields in mismatch_report.items()
        )
        raise ValueError(f"Species diffusion provenance is incompatible: {detail}.")

    prefactor = _ne_prefactor(
        temperature_k=conductivity.temperature_k,
        volume_a3=conductivity.volume_a3,
    )
    contributions = (
        counts.astype(np.float64)
        * group_charges**2
        * diffusion_values
        * prefactor
    )
    ne_value = float(np.sum(contributions))
    collective = float(conductivity.value_s_per_m)
    signed = collective - ne_value
    c_over_ne_defined = ne_value != 0.0
    ne_over_c_defined = collective != 0.0
    c_over_ne = collective / ne_value if c_over_ne_defined else float("nan")
    ne_over_c = ne_value / collective if ne_over_c_defined else float("nan")
    group_pair = np.asarray(conductivity.group_pair_values_s_per_m, dtype=np.float64)
    off_diagonal = float(np.sum(group_pair) - np.trace(group_pair))

    metadata: dict[str, Any] = {
        "contract_version": _C2_CONTRACT_VERSION,
        "schema": "mdstats.nernst_einstein_comparison.v1",
        "signed_difference_convention": "collective_minus_nernst_einstein",
        "ratio_zero_denominator_policy": "nan_with_explicit_defined_flag",
        "ratio_names_are_directional_not_universal_haven_labels": True,
        "ne_prefactor_s_per_m_per_e2_a2_per_ps": prefactor,
        "group_names": list(conductivity.group_names),
        "conductivity_estimate_metadata": conductivity.metadata,
        "diffusion_estimate_metadata": {
            name: species_diffusion[name].metadata for name in conductivity.group_names
        },
    }
    return NernstEinsteinComparisonResult(
        collective_conductivity_s_per_m=collective,
        nernst_einstein_conductivity_s_per_m=ne_value,
        signed_difference_s_per_m=signed,
        absolute_difference_s_per_m=abs(signed),
        collective_over_nernst_einstein=c_over_ne,
        nernst_einstein_over_collective=ne_over_c,
        collective_over_nernst_einstein_defined=c_over_ne_defined,
        nernst_einstein_over_collective_defined=ne_over_c_defined,
        group_names=conductivity.group_names,
        species_counts=counts,
        group_charges_e=group_charges,
        diffusion_a2_per_ps=diffusion_values,
        species_contributions_s_per_m=contributions,
        off_diagonal_group_contribution_s_per_m=off_diagonal,
        temperature_k=conductivity.temperature_k,
        volume_a3=conductivity.volume_a3,
        conductivity_time_range_ps=conductivity.time_range_ps,
        signature=conductivity.signature,
        metadata=metadata,
    )


__all__ = [
    "IonicConductivityEstimate",
    "IonicConductivityResult",
    "NernstEinsteinComparisonResult",
    "compute_nernst_einstein_comparison",
    "estimate_ionic_conductivity_plateau",
    "integrate_ionic_conductivity",
]
