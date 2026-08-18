"""Velocity spectra derived from stored velocity autocorrelations.

The module provides two estimators. ``compute_vacf_spectrum`` transforms a
stored :class:`~mdstats.analysis.vacf.VACFResult`;
``compute_velocity_spectrum`` estimates the spectrum directly from overlapping
windowed velocity segments. The autocorrelation/spectral-density relation
follows Wiener and Khintchine. The direct estimator follows Welch's method
[P. D. Welch, IEEE Trans. Audio Electroacoust. 15, 70-73 (1967), DOI:
10.1109/TAU.1967.1161901]. Velocity-correlation spectra as MD observables follow
Rahman [Phys. Rev. 136, A405-A411 (1964), DOI: 10.1103/PhysRev.136.A405].
SciPy supplies FFT and window implementations [Virtanen et al., Nature Methods
17, 261-272 (2020), DOI: 10.1038/s41592-019-0686-2].

The atom-selection and drift contract, weighted self-only aggregation,
atom-blocked accumulation, tensor layout, discrete normalization, and result
schemas are mdstats choices. No cross-atom current terms are introduced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias
import warnings

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.fft import next_fast_len, rfft, rfftfreq
from scipy.signal import get_window

from ..collection import AtomisticFrameCollection
from ._spectral import (
    LagWindowInput,
    make_atom_spectrum_plan,
    one_sided_density_scale,
    resolve_lag_window,
    resolve_spectrum_fft_length,
    spectral_bin_integral,
    transform_positive_lag_correlation,
)
from ._spectral_units import convert_frequency_axes
from ._velocity_common import DriftMode, WeightInput, prepare_velocity_inputs
from ._dynamics_common import (
    DynamicsInputSignature,
    freeze_mapping,
    owned_readonly_array,
    resolve_analysis_subspace,
)
from .selection import SpeciesSelection
from .vacf import (
    CollectiveMotionVACFWarning,
    FiniteDifferenceVelocityWarning,
    VACFResult,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
ComplexArray = NDArray[np.complex128]
SpectrumNormalization = Literal["raw", "per_weight"]
CorrelationWeighting = Literal["reported", "biased"]
NegativePolicy = Literal["preserve", "clip_roundoff", "error"]
VDOSNormalization = Literal["unit_area", "degrees_of_freedom", "none"]
VDOSNegativePolicy = Literal["error", "clip_roundoff"]
WelchDetrend = Literal["none", "constant"]
SegmentWindowInput: TypeAlias = str | tuple[str, float]


@dataclass(frozen=True, slots=True)
class VelocitySpectrumResult:
    """One-sided velocity spectral density and full estimator provenance."""

    frequencies_thz: FloatArray
    angular_frequencies_ps_inv: FloatArray
    wavenumbers_cm_inv: FloatArray
    energies_mev: FloatArray

    scalar_spectrum: FloatArray
    component_spectra: FloatArray
    tensor_spectrum: ComplexArray | None

    per_atom_scalar: FloatArray | None
    per_atom_components: FloatArray | None
    per_atom_indices: IntArray | None

    atom_indices: IntArray
    atom_weights: FloatArray
    weight_sum: float

    estimator: str
    weighting: str
    normalization: str
    correlation_weighting: str | None
    spectral_sidedness: str
    spectral_scaling: str
    spectrum_units: str
    sample_spacing_ps: float
    n_samples: int
    n_fft: int
    window: str | None
    detrend: str | None

    metadata: dict[str, Any] = field(default_factory=dict)
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        frequencies = np.asarray(self.frequencies_thz, dtype=np.float64)
        angular = np.asarray(self.angular_frequencies_ps_inv, dtype=np.float64)
        wavenumbers = np.asarray(self.wavenumbers_cm_inv, dtype=np.float64)
        energies = np.asarray(self.energies_mev, dtype=np.float64)
        scalar = np.asarray(self.scalar_spectrum, dtype=np.float64)
        components = np.asarray(self.component_spectra, dtype=np.float64)
        tensor = (
            None
            if self.tensor_spectrum is None
            else np.asarray(self.tensor_spectrum, dtype=np.complex128)
        )
        per_atom_scalar = (
            None
            if self.per_atom_scalar is None
            else np.asarray(self.per_atom_scalar, dtype=np.float64)
        )
        per_atom_components = (
            None
            if self.per_atom_components is None
            else np.asarray(self.per_atom_components, dtype=np.float64)
        )
        per_atom_indices = (
            None
            if self.per_atom_indices is None
            else np.asarray(self.per_atom_indices, dtype=np.int64)
        )
        atom_indices = np.asarray(self.atom_indices, dtype=np.int64)
        atom_weights = np.asarray(self.atom_weights, dtype=np.float64)

        n_frequency = int(frequencies.size)
        for name, value in (
            ("frequencies_thz", frequencies),
            ("angular_frequencies_ps_inv", angular),
            ("wavenumbers_cm_inv", wavenumbers),
            ("energies_mev", energies),
            ("scalar_spectrum", scalar),
        ):
            if value.shape != (n_frequency,):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected ({n_frequency},)."
                )
        if components.shape != (n_frequency, 3):
            raise ValueError(
                "component_spectra has shape "
                f"{components.shape}; expected ({n_frequency}, 3)."
            )
        if tensor is not None and tensor.shape != (n_frequency, 3, 3):
            raise ValueError(
                f"tensor_spectrum has shape {tensor.shape}; expected "
                f"({n_frequency}, 3, 3)."
            )

        if per_atom_indices is None:
            if per_atom_scalar is not None or per_atom_components is not None:
                raise ValueError(
                    "per_atom_indices is required when per-atom spectra exist."
                )
        else:
            n_output = int(per_atom_indices.size)
            if per_atom_scalar is None or per_atom_components is None:
                raise ValueError(
                    "Both per_atom_scalar and per_atom_components are required."
                )
            if per_atom_scalar.shape != (n_frequency, n_output):
                raise ValueError(
                    f"per_atom_scalar has shape {per_atom_scalar.shape}; expected "
                    f"({n_frequency}, {n_output})."
                )
            if per_atom_components.shape != (n_frequency, n_output, 3):
                raise ValueError(
                    "per_atom_components has shape "
                    f"{per_atom_components.shape}; expected "
                    f"({n_frequency}, {n_output}, 3)."
                )
            if not np.allclose(
                per_atom_scalar,
                np.sum(per_atom_components, axis=2),
                rtol=1.0e-11,
                atol=1.0e-12,
            ):
                raise ValueError(
                    "Per-atom scalar spectra must equal the Cartesian trace."
                )

        finite_real = [
            frequencies,
            angular,
            wavenumbers,
            energies,
            scalar,
            components,
            atom_weights,
        ]
        if per_atom_scalar is not None:
            finite_real.extend([per_atom_scalar, per_atom_components])
        if any(not np.all(np.isfinite(value)) for value in finite_real):
            raise ValueError("Velocity spectrum result contains non-finite values.")
        if tensor is not None and not (
            np.all(np.isfinite(tensor.real)) and np.all(np.isfinite(tensor.imag))
        ):
            raise ValueError("tensor_spectrum contains non-finite values.")

        if n_frequency < 1 or frequencies[0] != 0.0:
            raise ValueError("The frequency grid must be nonempty and start at zero.")
        if n_frequency > 1:
            increments = np.diff(frequencies)
            if np.any(increments <= 0.0) or not np.allclose(
                increments, increments[0], rtol=1.0e-12, atol=1.0e-14
            ):
                raise ValueError("The frequency grid must be uniformly increasing.")

        if not np.allclose(
            scalar,
            np.sum(components, axis=1),
            rtol=1.0e-11,
            atol=1.0e-12,
        ):
            raise ValueError("scalar_spectrum must equal the Cartesian trace.")
        if tensor is not None:
            diagonal = np.diagonal(tensor, axis1=1, axis2=2)
            if not np.allclose(
                diagonal.imag, 0.0, rtol=0.0, atol=2.0e-12
            ) or not np.allclose(
                diagonal.real, components, rtol=1.0e-11, atol=1.0e-12
            ):
                raise ValueError(
                    "The tensor diagonal must equal component_spectra and be real."
                )
            if not np.allclose(
                tensor,
                np.conjugate(np.swapaxes(tensor, 1, 2)),
                rtol=1.0e-11,
                atol=2.0e-12,
            ):
                raise ValueError("tensor_spectrum must be Hermitian at each frequency.")

        n_atoms = int(atom_indices.size)
        if atom_weights.shape != (n_atoms,):
            raise ValueError(
                f"atom_weights has shape {atom_weights.shape}; expected ({n_atoms},)."
            )
        if np.any(atom_weights < 0.0) or not np.any(atom_weights > 0.0):
            raise ValueError("atom_weights must be nonnegative and not all zero.")
        if not np.isfinite(self.weight_sum) or self.weight_sum <= 0.0:
            raise ValueError("weight_sum must be finite and strictly positive.")
        if not np.isclose(
            np.sum(atom_weights), self.weight_sum, rtol=1.0e-13, atol=1.0e-14
        ):
            raise ValueError("weight_sum is inconsistent with atom_weights.")
        if per_atom_indices is not None and not set(per_atom_indices.tolist()).issubset(
            set(atom_indices.tolist())
        ):
            raise ValueError("per_atom_indices must be a subset of atom_indices.")

        if self.estimator not in ("vacf_transform", "welch"):
            raise ValueError("Unsupported velocity-spectrum estimator.")
        if self.normalization not in ("raw", "per_weight"):
            raise ValueError("Unsupported spectrum normalization.")
        if self.spectral_sidedness != "one_sided":
            raise ValueError("Only one-sided spectra are currently supported.")
        if self.spectral_scaling != "density":
            raise ValueError("Only spectral-density scaling is currently supported.")
        if not np.isfinite(self.sample_spacing_ps) or self.sample_spacing_ps <= 0.0:
            raise ValueError("sample_spacing_ps must be finite and positive.")
        if isinstance(self.n_samples, bool) or self.n_samples < 1:
            raise ValueError("n_samples must be a positive integer.")
        if isinstance(self.n_fft, bool) or self.n_fft < 1:
            raise ValueError("n_fft must be a positive integer.")
        if n_frequency != self.n_fft // 2 + 1:
            raise ValueError("Frequency count is inconsistent with n_fft.")

        expected_frequency = np.arange(n_frequency, dtype=np.float64) / (
            float(self.n_fft) * float(self.sample_spacing_ps)
        )
        if not np.allclose(
            frequencies, expected_frequency, rtol=1.0e-12, atol=1.0e-14
        ):
            raise ValueError("Frequency grid is inconsistent with n_fft and spacing.")
        expected_axes = convert_frequency_axes(frequencies)
        for name, actual, expected in (
            ("angular-frequency", angular, expected_axes[0]),
            ("wavenumber", wavenumbers, expected_axes[1]),
            ("energy", energies, expected_axes[2]),
        ):
            if not np.allclose(actual, expected, rtol=1.0e-12, atol=1.0e-14):
                raise ValueError(f"The {name} axis is inconsistent with THz frequency.")

        object.__setattr__(self, "frequencies_thz", owned_readonly_array(frequencies, dtype=np.float64))
        object.__setattr__(self, "angular_frequencies_ps_inv", owned_readonly_array(angular, dtype=np.float64))
        object.__setattr__(self, "wavenumbers_cm_inv", owned_readonly_array(wavenumbers, dtype=np.float64))
        object.__setattr__(self, "energies_mev", owned_readonly_array(energies, dtype=np.float64))
        object.__setattr__(self, "scalar_spectrum", owned_readonly_array(scalar, dtype=np.float64))
        object.__setattr__(self, "component_spectra", owned_readonly_array(components, dtype=np.float64))
        object.__setattr__(self, "tensor_spectrum", None if tensor is None else owned_readonly_array(tensor, dtype=np.complex128))
        object.__setattr__(self, "per_atom_scalar", None if per_atom_scalar is None else owned_readonly_array(per_atom_scalar, dtype=np.float64))
        object.__setattr__(self, "per_atom_components", None if per_atom_components is None else owned_readonly_array(per_atom_components, dtype=np.float64))
        object.__setattr__(self, "per_atom_indices", None if per_atom_indices is None else owned_readonly_array(per_atom_indices, dtype=np.int64))
        object.__setattr__(self, "atom_indices", owned_readonly_array(atom_indices, dtype=np.int64))
        object.__setattr__(self, "atom_weights", owned_readonly_array(atom_weights, dtype=np.float64))
        object.__setattr__(self, "weight_sum", float(self.weight_sum))
        object.__setattr__(self, "n_samples", int(self.n_samples))
        object.__setattr__(self, "n_fft", int(self.n_fft))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not np.array_equal(self.signature.atom_indices, atom_indices):
                raise ValueError(
                    "signature atom_indices are inconsistent with VelocitySpectrumResult."
                )
            if not self.signature.subspace.same_physical_subspace(
                resolve_analysis_subspace()
            ):
                raise ValueError(
                    "A Cartesian VelocitySpectrumResult signature must use the full 3D subspace."
                )


def _validate_vacf_grid(vacf: VACFResult) -> float:
    if not isinstance(vacf, VACFResult):
        raise TypeError("vacf must be a VACFResult instance.")
    if vacf.lag_steps.size < 2:
        raise ValueError("VACF spectral transformation requires at least two lags.")
    expected_steps = np.arange(vacf.lag_steps.size, dtype=np.int64)
    if not np.array_equal(vacf.lag_steps, expected_steps):
        raise ValueError(
            "VACF spectral transformation requires contiguous saved-frame lags "
            "starting at zero."
        )
    if not np.isclose(vacf.lag_times[0], 0.0, rtol=0.0, atol=1.0e-14):
        raise ValueError("VACF lag_times must start at zero.")
    increments = np.diff(vacf.lag_times)
    if np.any(increments <= 0.0) or not np.allclose(
        increments, increments[0], rtol=1.0e-10, atol=1.0e-14
    ):
        raise ValueError("VACF lag_times must form a uniform increasing grid.")
    return float(increments[0])


def _real_correlation_spectrum(
    values: ComplexArray,
    *,
    label: str,
) -> FloatArray:
    scale = max(1.0, float(np.max(np.abs(values.real))))
    tolerance = 2000.0 * np.finfo(np.float64).eps * scale
    if np.max(np.abs(values.imag)) > tolerance:
        raise ValueError(
            f"{label} acquired a non-negligible imaginary part; the input is not "
            "a valid even self-correlation under the current convention."
        )
    return np.asarray(values.real, dtype=np.float64)


def _apply_negative_policy(
    values: FloatArray,
    *,
    policy: NegativePolicy,
    tolerance: float,
    label: str,
) -> FloatArray:
    result = np.array(values, dtype=np.float64, copy=True)
    projection_scale = np.max(np.abs(result), axis=0, keepdims=True)
    projection_scale = np.maximum(1.0, projection_scale)
    threshold = float(tolerance) * projection_scale
    materially_negative = result < -threshold
    roundoff_negative = (result < 0.0) & ~materially_negative

    if policy == "error" and np.any(materially_negative):
        minimum = float(np.min(result))
        raise ValueError(
            f"{label} contains a material negative value ({minimum:.6g}); use "
            "negative_policy='preserve' to retain diagnostic negative lobes."
        )
    if policy in ("clip_roundoff", "error"):
        result[roundoff_negative] = 0.0
    return result


def _spectrum_units(vacf: VACFResult, normalization: str) -> str:
    return _density_units_from_correlation(
        str(vacf.metadata.get("correlation_units", "unknown")),
        weighting=vacf.weighting,
        normalization=normalization,
    )


def compute_vacf_spectrum(
    vacf: VACFResult,
    *,
    normalization: SpectrumNormalization = "per_weight",
    correlation_weighting: CorrelationWeighting = "reported",
    window: LagWindowInput | None = None,
    zero_pad_to: int | None = None,
    sidedness: Literal["one_sided"] = "one_sided",
    negative_policy: NegativePolicy = "preserve",
    negative_tolerance: float = 1.0e-12,
) -> VelocitySpectrumResult:
    """Transform a stored positive-lag VACF into a one-sided spectrum.

    ``correlation_weighting='reported'`` transforms the correlation exactly as
    stored.  ``'biased'`` first multiplies lag ``k`` by
    ``n_origins[k] / n_origins[0]``; for a contiguous all-origin record this is
    the triangular weighting associated with the finite-record periodogram.

    The method follows the Wiener-Khinchin autocorrelation/spectrum relation.
    The estimator switch, positive-lag tensor reconstruction, and result
    conventions are mdstats-specific and are never applied implicitly.
    """

    dt_ps = _validate_vacf_grid(vacf)
    if normalization not in ("raw", "per_weight"):
        raise ValueError("normalization must be 'raw' or 'per_weight'.")
    if correlation_weighting not in ("reported", "biased"):
        raise ValueError(
            "correlation_weighting must be 'reported' or 'biased'."
        )
    if sidedness != "one_sided":
        raise ValueError("Only sidedness='one_sided' is currently supported.")
    if negative_policy not in ("preserve", "clip_roundoff", "error"):
        raise ValueError(
            "negative_policy must be 'preserve', 'clip_roundoff', or 'error'."
        )
    if not np.isfinite(negative_tolerance) or negative_tolerance < 0.0:
        raise ValueError("negative_tolerance must be finite and nonnegative.")

    lag_window, window_metadata = resolve_lag_window(window, vacf.lag_steps.size)
    n_fft = resolve_spectrum_fft_length(
        int(vacf.lag_steps.size), zero_pad_to=zero_pad_to
    )

    normalization_factor = 1.0 if normalization == "raw" else vacf.weight_sum
    origin_factor = np.ones(vacf.lag_steps.size, dtype=np.float64)
    if correlation_weighting == "biased":
        origin_factor = vacf.n_origins.astype(np.float64) / float(vacf.n_origins[0])
    lag_factor = origin_factor * lag_window / float(normalization_factor)

    def weighted(values: FloatArray) -> FloatArray:
        return np.asarray(values, dtype=np.float64) * lag_factor.reshape(
            (lag_factor.size,) + (1,) * (np.ndim(values) - 1)
        )

    frequencies, component_complex = transform_positive_lag_correlation(
        weighted(vacf.components_sum), dt_ps=dt_ps, n_fft=n_fft
    )
    components = _real_correlation_spectrum(
        component_complex, label="Cartesian VACF spectrum"
    )

    scalar_frequency, scalar_complex = transform_positive_lag_correlation(
        weighted(vacf.scalar_sum), dt_ps=dt_ps, n_fft=n_fft
    )
    if not np.array_equal(frequencies, scalar_frequency):
        raise RuntimeError("Internal spectrum transforms produced inconsistent grids.")
    scalar_direct = _real_correlation_spectrum(
        scalar_complex, label="scalar VACF spectrum"
    )
    if not np.allclose(
        scalar_direct,
        np.sum(components, axis=1),
        rtol=1.0e-11,
        atol=1.0e-12,
    ):
        raise RuntimeError("Scalar and Cartesian VACF transforms are inconsistent.")

    tensor: ComplexArray | None = None
    if vacf.tensor_sum is not None:
        tensor_frequency, tensor = transform_positive_lag_correlation(
            weighted(vacf.tensor_sum),
            dt_ps=dt_ps,
            n_fft=n_fft,
            tensor_axes=(1, 2),
        )
        if not np.array_equal(frequencies, tensor_frequency):
            raise RuntimeError("Internal tensor transform produced a different grid.")
        if not np.allclose(
            tensor,
            np.conjugate(np.swapaxes(tensor, 1, 2)),
            rtol=1.0e-11,
            atol=2.0e-12,
        ):
            raise RuntimeError("Reconstructed VACF tensor spectrum is not Hermitian.")
        if not np.allclose(
            np.diagonal(tensor, axis1=1, axis2=2).real,
            components,
            rtol=1.0e-11,
            atol=1.0e-12,
        ):
            raise RuntimeError("Tensor and component VACF transforms are inconsistent.")

    per_atom_components: FloatArray | None = None
    per_atom_scalar: FloatArray | None = None
    if vacf.per_atom_components is not None:
        per_frequency, per_complex = transform_positive_lag_correlation(
            weighted(vacf.per_atom_components), dt_ps=dt_ps, n_fft=n_fft
        )
        if not np.array_equal(frequencies, per_frequency):
            raise RuntimeError("Internal per-atom transform produced a different grid.")
        per_atom_components = _real_correlation_spectrum(
            per_complex, label="per-atom VACF spectrum"
        )
        per_scalar_frequency, per_scalar_complex = (
            transform_positive_lag_correlation(
                weighted(vacf.per_atom_scalar), dt_ps=dt_ps, n_fft=n_fft
            )
        )
        if not np.array_equal(frequencies, per_scalar_frequency):
            raise RuntimeError(
                "Internal per-atom scalar transform produced a different grid."
            )
        per_scalar_direct = _real_correlation_spectrum(
            per_scalar_complex, label="per-atom scalar VACF spectrum"
        )
        if not np.allclose(
            per_scalar_direct,
            np.sum(per_atom_components, axis=2),
            rtol=1.0e-11,
            atol=1.0e-12,
        ):
            raise RuntimeError(
                "Per-atom scalar and component VACF transforms are inconsistent."
            )

    components = _apply_negative_policy(
        components,
        policy=negative_policy,
        tolerance=negative_tolerance,
        label="Cartesian VACF spectrum",
    )
    if per_atom_components is not None:
        per_atom_components = _apply_negative_policy(
            per_atom_components,
            policy=negative_policy,
            tolerance=negative_tolerance,
            label="per-atom VACF spectrum",
        )
        per_atom_scalar = np.sum(per_atom_components, axis=2)

    scalar = np.sum(components, axis=1)
    if tensor is not None:
        tensor = np.array(tensor, dtype=np.complex128, copy=True)
        diagonal_indices = np.arange(3)
        tensor[:, diagonal_indices, diagonal_indices] = components.astype(
            np.complex128
        )

    angular, wavenumbers, energies = convert_frequency_axes(frequencies)
    source_frame_count = vacf.metadata.get("frame_count")
    n_samples = (
        int(source_frame_count)
        if isinstance(source_frame_count, (int, np.integer))
        and int(source_frame_count) > 0
        else int(vacf.n_origins[0])
    )

    metadata: dict[str, Any] = {
        "source_analysis": "VACF",
        "source_backend": vacf.backend,
        "source_vacf_metadata": dict(vacf.metadata),
        "source_n_lags": int(vacf.lag_steps.size),
        "source_max_lag_ps": float(vacf.lag_times[-1]),
        "source_origin_counts": vacf.n_origins.tolist(),
        "lag_window": dict(window_metadata),
        "origin_weighting_factor": origin_factor.tolist(),
        "zero_padding_requested": zero_pad_to,
        "negative_policy": negative_policy,
        "negative_tolerance": float(negative_tolerance),
        "fourier_frequency_convention": "cycles_per_ps",
        "zero_padding_interpretation": "frequency_grid_refinement_only",
    }

    return VelocitySpectrumResult(
        frequencies_thz=frequencies,
        angular_frequencies_ps_inv=angular,
        wavenumbers_cm_inv=wavenumbers,
        energies_mev=energies,
        scalar_spectrum=scalar,
        component_spectra=components,
        tensor_spectrum=tensor,
        per_atom_scalar=per_atom_scalar,
        per_atom_components=per_atom_components,
        per_atom_indices=(
            None
            if vacf.per_atom_indices is None
            else np.array(vacf.per_atom_indices, dtype=np.int64, copy=True)
        ),
        atom_indices=np.array(vacf.atom_indices, dtype=np.int64, copy=True),
        atom_weights=np.array(vacf.atom_weights, dtype=np.float64, copy=True),
        weight_sum=vacf.weight_sum,
        estimator="vacf_transform",
        weighting=vacf.weighting,
        normalization=normalization,
        correlation_weighting=correlation_weighting,
        spectral_sidedness="one_sided",
        spectral_scaling="density",
        spectrum_units=_spectrum_units(vacf, normalization),
        sample_spacing_ps=dt_ps,
        n_samples=n_samples,
        n_fft=n_fft,
        window=window_metadata["name"],
        detrend=None,
        metadata=metadata,
        signature=vacf.signature,
    )


def _require_welch_integer(value: object, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise TypeError(f"{name} must be an integer.")
    resolved = int(value)
    if resolved < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")
    return resolved


def _resolve_welch_segment_length(
    n_samples: int, segment_length: int | None
) -> int:
    if segment_length is None:
        return min(256, int(n_samples))
    resolved = _require_welch_integer(
        segment_length, name="segment_length", minimum=2
    )
    if resolved > n_samples:
        raise ValueError(
            f"segment_length={resolved} exceeds the {n_samples} available samples."
        )
    return resolved


def _resolve_welch_overlap(
    overlap: float | int, segment_length: int
) -> tuple[int, int]:
    if isinstance(overlap, (bool, np.bool_)):
        raise TypeError("overlap must be a fraction or an integer sample count.")
    if isinstance(overlap, (int, np.integer)):
        n_overlap = int(overlap)
        if n_overlap < 0:
            raise ValueError("Integer overlap must be nonnegative.")
    elif isinstance(overlap, (float, np.floating)):
        fraction = float(overlap)
        if not np.isfinite(fraction) or not 0.0 <= fraction < 1.0:
            raise ValueError("Floating overlap must satisfy 0 <= overlap < 1.")
        n_overlap = int(np.floor(fraction * segment_length))
    else:
        raise TypeError("overlap must be a fraction or an integer sample count.")
    if n_overlap >= segment_length:
        raise ValueError("overlap must be smaller than segment_length.")
    advance = segment_length - n_overlap
    return n_overlap, advance


def _resolve_welch_fft_length(
    segment_length: int, zero_pad_to: int | None
) -> int:
    lower_bound = int(segment_length)
    if zero_pad_to is not None:
        lower_bound = max(
            lower_bound,
            _require_welch_integer(zero_pad_to, name="zero_pad_to", minimum=1),
        )
    return int(next_fast_len(lower_bound))


def _resolve_segment_window(
    window: SegmentWindowInput, segment_length: int
) -> tuple[FloatArray, str, dict[str, Any]]:
    if not isinstance(window, (str, tuple)):
        raise TypeError("window must be a SciPy window name or (name, parameter) tuple.")
    if isinstance(window, tuple):
        if len(window) != 2 or not isinstance(window[0], str):
            raise ValueError("Parameterized window must be a (name, parameter) tuple.")
        try:
            parameter = float(window[1])
        except (TypeError, ValueError) as exc:
            raise TypeError("Window parameter must be numeric.") from exc
        if not np.isfinite(parameter):
            raise ValueError("Window parameter must be finite.")
        resolved_spec: str | tuple[str, float] = (window[0], parameter)
        label = f"{window[0]}({parameter:g})"
        metadata_spec: str | list[object] = [window[0], parameter]
    else:
        if not window:
            raise ValueError("window name must not be empty.")
        resolved_spec = window
        label = window
        metadata_spec = window
    try:
        values = np.asarray(
            get_window(resolved_spec, segment_length, fftbins=True),
            dtype=np.float64,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Welch window specification {window!r}.") from exc
    if values.shape != (segment_length,) or not np.all(np.isfinite(values)):
        raise ValueError("Resolved Welch window is invalid.")
    energy = float(np.dot(values, values))
    if not np.isfinite(energy) or energy <= 0.0:
        raise ValueError("Welch window must have positive finite squared energy.")
    metadata = {
        "specification": metadata_spec,
        "fftbins": True,
        "sum": float(np.sum(values)),
        "sum_squares": energy,
    }
    return values, label, metadata


def _density_units_from_correlation(
    correlation_units: str, *, weighting: str, normalization: str
) -> str:
    units = str(correlation_units)
    if normalization == "per_weight" and weighting == "mass":
        prefix = "amu*"
        if units.startswith(prefix):
            units = units[len(prefix) :]
    if units.endswith("/ps^2"):
        return units[: -len("/ps^2")] + "/ps"
    if units == "unknown":
        return "unknown"
    return units + "*ps"


def compute_velocity_spectrum(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    weights: WeightInput = "uniform",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    segment_length: int | None = None,
    overlap: float | int = 0.5,
    window: SegmentWindowInput = "hann",
    detrend: WelchDetrend = "none",
    zero_pad_to: int | None = None,
    compute_tensor: bool = True,
    per_atom: bool = False,
    per_atom_indices: ArrayLike | None = None,
    atom_block_size: int | None = None,
    memory_target_bytes: int = 256_000_000,
) -> VelocitySpectrumResult:
    """Estimate a one-sided self velocity PSD by Welch segment averaging.

    Welch's published method divides a record into overlapping segments,
    windows each segment, forms modified periodograms, and averages them.
    mdstats applies that method independently to each measured atom and then
    sums only self periodograms. It never forms products between distinct
    atoms. Physical drift removal precedes the optional segmentwise detrend.
    """

    if not isinstance(compute_tensor, (bool, np.bool_)):
        raise TypeError("compute_tensor must be boolean.")
    if not isinstance(per_atom, (bool, np.bool_)):
        raise TypeError("per_atom must be boolean.")
    if detrend not in ("none", "constant"):
        raise ValueError("detrend must be 'none' or 'constant'.")

    inputs = prepare_velocity_inputs(
        collection,
        analysis_name="Welch velocity spectrum",
        species=species,
        atom_indices=atom_indices,
        weights=weights,
        drift_mode=drift_mode,
        drift_species=drift_species,
        drift_atom_indices=drift_atom_indices,
        per_atom=bool(per_atom),
        per_atom_indices=per_atom_indices,
    )
    if inputs.drift_matches_measured_subset:
        warnings.warn(
            "The drift reference equals the measured subset; subtracting it "
            "removes collective translation of that subset.",
            CollectiveMotionVACFWarning,
            stacklevel=2,
        )

    n_samples = int(collection.n_frames)
    resolved_segment = _resolve_welch_segment_length(n_samples, segment_length)
    n_overlap, advance = _resolve_welch_overlap(overlap, resolved_segment)
    starts = np.arange(
        0, n_samples - resolved_segment + 1, advance, dtype=np.int64
    )
    if starts.size < 1:
        raise RuntimeError("No complete Welch segment could be formed.")
    segment_window, window_label, window_metadata = _resolve_segment_window(
        window, resolved_segment
    )
    n_fft = _resolve_welch_fft_length(resolved_segment, zero_pad_to)
    plan = make_atom_spectrum_plan(
        int(inputs.atom_indices.size),
        resolved_segment,
        n_fft,
        atom_block_size=atom_block_size,
        memory_target_bytes=memory_target_bytes,
    )

    n_frequency = plan.n_frequency
    components = np.zeros((n_frequency, 3), dtype=np.float64)
    tensor = (
        np.zeros((n_frequency, 3, 3), dtype=np.complex128)
        if compute_tensor
        else None
    )
    n_output = (
        0 if inputs.per_atom_indices is None else int(inputs.per_atom_indices.size)
    )
    per_components = (
        None
        if n_output == 0
        else np.zeros((n_frequency, n_output, 3), dtype=np.float64)
    )
    output_lookup = np.full(inputs.atom_indices.size, -1, dtype=np.int64)
    if inputs.per_atom_local_indices is not None:
        output_lookup[inputs.per_atom_local_indices] = np.arange(
            n_output, dtype=np.int64
        )

    sqrt_weights = np.sqrt(inputs.atom_weights)
    for start in starts:
        stop = int(start) + resolved_segment
        drift_segment = (
            None
            if inputs.drift_velocity is None
            else inputs.drift_velocity[int(start) : stop]
        )
        for block_start in range(0, inputs.atom_indices.size, plan.atom_block_size):
            block_stop = min(
                inputs.atom_indices.size, block_start + plan.atom_block_size
            )
            canonical = inputs.atom_indices[block_start:block_stop]
            values = np.asarray(
                inputs.velocities[int(start) : stop, canonical, :],
                dtype=np.float64,
            )
            if drift_segment is not None:
                values = values - drift_segment[:, None, :]
            else:
                values = np.array(values, dtype=np.float64, copy=True)
            if detrend == "constant":
                values -= np.mean(values, axis=0, keepdims=True)
            values *= sqrt_weights[None, block_start:block_stop, None]
            values *= segment_window[:, None, None]
            transformed = rfft(values, n=n_fft, axis=0)
            power = np.abs(transformed) ** 2
            components += np.sum(power, axis=1)
            if tensor is not None:
                tensor += np.einsum(
                    "fba,fbc->fac",
                    np.conjugate(transformed),
                    transformed,
                    optimize=True,
                )
            if per_components is not None:
                positions = output_lookup[block_start:block_stop]
                mask = positions >= 0
                if np.any(mask):
                    per_components[:, positions[mask], :] += power[:, mask, :]

    sampling_frequency_per_ps = 1.0 / inputs.sample_spacing_ps
    window_energy = float(window_metadata["sum_squares"])
    scale = one_sided_density_scale(n_fft) / (
        float(starts.size) * sampling_frequency_per_ps * window_energy
    )
    components *= scale[:, None]
    scalar = np.sum(components, axis=1)
    if tensor is not None:
        tensor *= scale[:, None, None]
        diagonal = np.arange(3)
        tensor[:, diagonal, diagonal] = components.astype(np.complex128)
    per_scalar: FloatArray | None = None
    if per_components is not None:
        per_components *= scale[:, None, None]
        per_scalar = np.sum(per_components, axis=2)

    frequencies = rfftfreq(n_fft, d=inputs.sample_spacing_ps).astype(
        np.float64, copy=False
    )
    angular, wavenumbers, energies = convert_frequency_axes(frequencies)
    velocity_source = collection.provenance.velocity_source
    if velocity_source == "finite_difference":
        warnings.warn(
            "Velocities were reconstructed by finite difference; high-frequency "
            "velocity-spectrum amplitudes may be attenuated.",
            FiniteDifferenceVelocityWarning,
            stacklevel=2,
        )

    last_stop = int(starts[-1]) + resolved_segment
    metadata: dict[str, Any] = {
        "source_analysis": "trajectory_velocities",
        "selected_atom_indices": inputs.atom_indices.tolist(),
        "per_atom_indices": (
            None
            if inputs.per_atom_indices is None
            else inputs.per_atom_indices.tolist()
        ),
        "weighting": inputs.weighting,
        "weight_units": inputs.weight_units,
        "velocity_units": "Å/ps",
        "velocity_source": velocity_source,
        "drift_mode": inputs.drift_mode,
        "drift_atom_indices": (
            None
            if inputs.drift_atom_indices is None
            else inputs.drift_atom_indices.tolist()
        ),
        "segment_length": resolved_segment,
        "overlap_input": float(overlap) if isinstance(overlap, (float, np.floating)) else int(overlap),
        "overlap_samples": n_overlap,
        "advance_samples": advance,
        "segment_count": int(starts.size),
        "segment_starts": starts.tolist(),
        "discarded_tail_samples": n_samples - last_stop,
        "window": dict(window_metadata),
        "detrend": detrend,
        "sampling_frequency_per_ps": sampling_frequency_per_ps,
        "window_density_denominator": sampling_frequency_per_ps * window_energy,
        "zero_padding_requested": zero_pad_to,
        "fft_length": n_fft,
        "atom_block_size": plan.atom_block_size,
        "estimated_atom_block_work_bytes": plan.estimated_work_bytes,
        "memory_target_bytes": int(memory_target_bytes),
        "compute_tensor": bool(compute_tensor),
        "self_terms_only": True,
        "cross_atom_products_included": False,
        "fourier_frequency_convention": "cycles_per_ps",
        "spectral_sidedness": "one_sided",
        "spectral_scaling": "density",
        "source_format": collection.provenance.source_format,
        "source_files": list(collection.provenance.source_files),
        "frame_count": n_samples,
        "frame_id_first": int(collection.frame_ids[0]),
        "frame_id_last": int(collection.frame_ids[-1]),
        "time_start_ps": float(collection.times[0]),
        "time_end_ps": float(collection.times[-1]),
    }

    return VelocitySpectrumResult(
        frequencies_thz=frequencies,
        angular_frequencies_ps_inv=angular,
        wavenumbers_cm_inv=wavenumbers,
        energies_mev=energies,
        scalar_spectrum=scalar,
        component_spectra=components,
        tensor_spectrum=tensor,
        per_atom_scalar=per_scalar,
        per_atom_components=per_components,
        per_atom_indices=(
            None
            if inputs.per_atom_indices is None
            else np.array(inputs.per_atom_indices, dtype=np.int64, copy=True)
        ),
        atom_indices=np.array(inputs.atom_indices, dtype=np.int64, copy=True),
        atom_weights=np.array(inputs.atom_weights, dtype=np.float64, copy=True),
        weight_sum=inputs.weight_sum,
        estimator="welch",
        weighting=inputs.weighting,
        normalization="raw",
        correlation_weighting=None,
        spectral_sidedness="one_sided",
        spectral_scaling="density",
        spectrum_units=_density_units_from_correlation(
            inputs.correlation_units,
            weighting=inputs.weighting,
            normalization="raw",
        ),
        sample_spacing_ps=inputs.sample_spacing_ps,
        n_samples=n_samples,
        n_fft=n_fft,
        window=window_label,
        detrend=detrend,
        metadata=metadata,
        signature=inputs.signature,
    )



@dataclass(frozen=True, slots=True)
class VDOSResult:
    """Explicitly normalized finite-temperature vibrational density of states."""

    frequencies_thz: FloatArray
    wavenumbers_cm_inv: FloatArray
    energies_mev: FloatArray

    total: FloatArray
    components: FloatArray
    per_atom: FloatArray | None
    per_atom_components: FloatArray | None
    per_atom_indices: IntArray | None

    normalization: str
    integrated_weight_before: float
    integrated_weight_after: float
    target_weight: float | None
    source_estimator: str
    weighting: str
    density_units: str
    metadata: dict[str, Any] = field(default_factory=dict)
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        frequencies = np.asarray(self.frequencies_thz, dtype=np.float64)
        wavenumbers = np.asarray(self.wavenumbers_cm_inv, dtype=np.float64)
        energies = np.asarray(self.energies_mev, dtype=np.float64)
        total = np.asarray(self.total, dtype=np.float64)
        components = np.asarray(self.components, dtype=np.float64)
        per_atom = (
            None if self.per_atom is None else np.asarray(self.per_atom, dtype=np.float64)
        )
        per_atom_components = (
            None
            if self.per_atom_components is None
            else np.asarray(self.per_atom_components, dtype=np.float64)
        )
        per_atom_indices = (
            None
            if self.per_atom_indices is None
            else np.asarray(self.per_atom_indices, dtype=np.int64)
        )

        n_frequency = int(frequencies.size)
        if n_frequency < 2:
            raise ValueError("VDOSResult requires at least two frequency bins.")
        for name, value in (
            ("frequencies_thz", frequencies),
            ("wavenumbers_cm_inv", wavenumbers),
            ("energies_mev", energies),
            ("total", total),
        ):
            if value.shape != (n_frequency,):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected ({n_frequency},)."
                )
        if components.shape != (n_frequency, 3):
            raise ValueError(
                f"components has shape {components.shape}; expected "
                f"({n_frequency}, 3)."
            )

        if per_atom_indices is None:
            if per_atom is not None or per_atom_components is not None:
                raise ValueError(
                    "per_atom_indices is required when per-atom VDOS data exist."
                )
        else:
            n_atoms = int(per_atom_indices.size)
            if per_atom is None or per_atom_components is None:
                raise ValueError(
                    "Both per_atom and per_atom_components are required."
                )
            if per_atom.shape != (n_frequency, n_atoms):
                raise ValueError(
                    f"per_atom has shape {per_atom.shape}; expected "
                    f"({n_frequency}, {n_atoms})."
                )
            if per_atom_components.shape != (n_frequency, n_atoms, 3):
                raise ValueError(
                    "per_atom_components has shape "
                    f"{per_atom_components.shape}; expected "
                    f"({n_frequency}, {n_atoms}, 3)."
                )
            if not np.allclose(
                per_atom,
                np.sum(per_atom_components, axis=2),
                rtol=1.0e-11,
                atol=1.0e-12,
            ):
                raise ValueError("per_atom must equal the Cartesian trace.")

        arrays = [frequencies, wavenumbers, energies, total, components]
        if per_atom is not None:
            arrays.extend([per_atom, per_atom_components])
        if any(not np.all(np.isfinite(value)) for value in arrays):
            raise ValueError("VDOSResult contains non-finite values.")
        if frequencies[0] < 0.0:
            raise ValueError("VDOS frequencies must be nonnegative.")
        increments = np.diff(frequencies)
        if np.any(increments <= 0.0) or not np.allclose(
            increments,
            increments[0],
            rtol=1.0e-12,
            atol=max(1.0e-14, 1.0e-12 * abs(float(increments[0]))),
        ):
            raise ValueError("VDOS frequencies must be uniformly increasing.")

        _, expected_wavenumbers, expected_energies = convert_frequency_axes(
            frequencies
        )
        if not np.allclose(
            wavenumbers, expected_wavenumbers, rtol=1.0e-12, atol=1.0e-14
        ):
            raise ValueError("wavenumbers_cm_inv is inconsistent with frequency.")
        if not np.allclose(
            energies, expected_energies, rtol=1.0e-12, atol=1.0e-14
        ):
            raise ValueError("energies_mev is inconsistent with frequency.")

        if np.any(total < 0.0) or np.any(components < 0.0):
            raise ValueError("VDOS total and component values must be nonnegative.")
        if per_atom is not None and (
            np.any(per_atom < 0.0) or np.any(per_atom_components < 0.0)
        ):
            raise ValueError("Per-atom VDOS values must be nonnegative.")
        if not np.allclose(
            total,
            np.sum(components, axis=1),
            rtol=1.0e-11,
            atol=1.0e-12,
        ):
            raise ValueError("total must equal the Cartesian component sum.")

        if self.normalization not in ("unit_area", "degrees_of_freedom", "none"):
            raise ValueError("Unsupported VDOS normalization.")
        if self.source_estimator not in ("vacf_transform", "welch"):
            raise ValueError("Unsupported source spectrum estimator.")
        if not isinstance(self.weighting, str) or not self.weighting:
            raise ValueError("weighting must be a nonempty string.")
        if not isinstance(self.density_units, str) or not self.density_units:
            raise ValueError("density_units must be a nonempty string.")

        before = float(self.integrated_weight_before)
        after = float(self.integrated_weight_after)
        if not np.isfinite(before) or before <= 0.0:
            raise ValueError("integrated_weight_before must be finite and positive.")
        if not np.isfinite(after) or after <= 0.0:
            raise ValueError("integrated_weight_after must be finite and positive.")
        measured_after = float(spectral_bin_integral(total, frequencies))
        if not np.isclose(measured_after, after, rtol=1.0e-11, atol=1.0e-13):
            raise ValueError("integrated_weight_after is inconsistent with total.")

        target = None if self.target_weight is None else float(self.target_weight)
        if self.normalization == "none":
            if target is not None:
                raise ValueError("normalization='none' requires target_weight=None.")
        else:
            if target is None or not np.isfinite(target) or target <= 0.0:
                raise ValueError("Normalized VDOS results require a positive target.")
            if not np.isclose(after, target, rtol=1.0e-11, atol=1.0e-13):
                raise ValueError("integrated_weight_after does not match target_weight.")
            if self.normalization == "unit_area" and not np.isclose(
                target, 1.0, rtol=0.0, atol=1.0e-14
            ):
                raise ValueError("unit_area normalization requires target_weight=1.")

        object.__setattr__(self, "frequencies_thz", owned_readonly_array(frequencies, dtype=np.float64))
        object.__setattr__(self, "wavenumbers_cm_inv", owned_readonly_array(wavenumbers, dtype=np.float64))
        object.__setattr__(self, "energies_mev", owned_readonly_array(energies, dtype=np.float64))
        object.__setattr__(self, "total", owned_readonly_array(total, dtype=np.float64))
        object.__setattr__(self, "components", owned_readonly_array(components, dtype=np.float64))
        object.__setattr__(self, "per_atom", None if per_atom is None else owned_readonly_array(per_atom, dtype=np.float64))
        object.__setattr__(self, "per_atom_components", None if per_atom_components is None else owned_readonly_array(per_atom_components, dtype=np.float64))
        object.__setattr__(self, "per_atom_indices", None if per_atom_indices is None else owned_readonly_array(per_atom_indices, dtype=np.int64))
        object.__setattr__(self, "integrated_weight_before", before)
        object.__setattr__(self, "integrated_weight_after", after)
        object.__setattr__(self, "target_weight", target)
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not self.signature.subspace.same_physical_subspace(
                resolve_analysis_subspace()
            ):
                raise ValueError("A Cartesian VDOSResult signature must use the full 3D subspace.")


def _sanitize_vdos_values(
    values: FloatArray,
    *,
    policy: VDOSNegativePolicy,
    tolerance: float,
    label: str,
) -> FloatArray:
    result = np.array(values, dtype=np.float64, copy=True)
    if policy == "error":
        if np.any(result < 0.0):
            raise ValueError(f"{label} contains negative spectral values.")
        return result

    projection_scale = np.max(np.abs(result), axis=0, keepdims=True)
    projection_scale = np.maximum(1.0, projection_scale)
    threshold = float(tolerance) * projection_scale
    materially_negative = result < -threshold
    if np.any(materially_negative):
        minimum = float(np.min(result))
        raise ValueError(
            f"{label} contains a material negative value ({minimum:.6g}); "
            "VDOS normalization may clip roundoff only."
        )
    result[result < 0.0] = 0.0
    return result


def compute_vdos(
    spectrum: VelocitySpectrumResult,
    *,
    normalization: VDOSNormalization = "unit_area",
    target_degrees_of_freedom: float | None = None,
    minimum_frequency_thz: float | None = None,
    negative_policy: VDOSNegativePolicy = "clip_roundoff",
    negative_tolerance: float = 1.0e-12,
) -> VDOSResult:
    """Normalize a one-sided velocity spectrum into an explicit VDOS.

    Velocity-correlation spectra are established MD observables [Rahman,
    Phys. Rev. 136, A405-A411 (1964), DOI: 10.1103/PhysRev.136.A405]. The
    related VACF-derived two-phase thermodynamic method is due to Lin, Blanco,
    and Goddard [J. Chem. Phys. 119, 11792-11805 (2003), DOI:
    10.1063/1.1624057], but is not implemented here. The discrete one-sided
    bin normalization, explicit degree-of-freedom target, low-frequency crop,
    and material-negative rejection are mdstats choices.
    """

    if not isinstance(spectrum, VelocitySpectrumResult):
        raise TypeError("spectrum must be a VelocitySpectrumResult instance.")
    if spectrum.spectral_sidedness != "one_sided":
        raise ValueError("VDOS requires a one-sided source spectrum.")
    if spectrum.spectral_scaling != "density":
        raise ValueError("VDOS requires spectral-density scaling.")
    if normalization not in ("unit_area", "degrees_of_freedom", "none"):
        raise ValueError(
            "normalization must be 'unit_area', 'degrees_of_freedom', or 'none'."
        )
    if negative_policy not in ("error", "clip_roundoff"):
        raise ValueError("negative_policy must be 'error' or 'clip_roundoff'.")
    if not np.isfinite(negative_tolerance) or negative_tolerance < 0.0:
        raise ValueError("negative_tolerance must be finite and nonnegative.")

    if normalization == "degrees_of_freedom":
        if target_degrees_of_freedom is None:
            raise ValueError(
                "target_degrees_of_freedom is required for degrees_of_freedom "
                "normalization."
            )
        target = float(target_degrees_of_freedom)
        if not np.isfinite(target) or target <= 0.0:
            raise ValueError(
                "target_degrees_of_freedom must be finite and strictly positive."
            )
    else:
        if target_degrees_of_freedom is not None:
            raise ValueError(
                "target_degrees_of_freedom is only valid for "
                "normalization='degrees_of_freedom'."
            )
        target = 1.0 if normalization == "unit_area" else None

    frequencies = np.asarray(spectrum.frequencies_thz, dtype=np.float64)
    first_retained = 0
    threshold = None
    if minimum_frequency_thz is not None:
        threshold = float(minimum_frequency_thz)
        if not np.isfinite(threshold) or threshold < 0.0:
            raise ValueError(
                "minimum_frequency_thz must be finite and nonnegative."
            )
        first_retained = int(np.searchsorted(frequencies, threshold, side="left"))
    retained = slice(first_retained, None)
    frequencies = np.array(frequencies[retained], dtype=np.float64, copy=True)
    if frequencies.size < 2:
        raise ValueError(
            "VDOS normalization requires at least two retained frequency bins."
        )

    components = _sanitize_vdos_values(
        spectrum.component_spectra[retained],
        policy=negative_policy,
        tolerance=negative_tolerance,
        label="Cartesian velocity spectrum",
    )
    total = np.sum(components, axis=1, dtype=np.float64)

    per_atom_components: FloatArray | None = None
    per_atom: FloatArray | None = None
    per_atom_indices: IntArray | None = None
    if spectrum.per_atom_components is not None:
        per_atom_components = _sanitize_vdos_values(
            spectrum.per_atom_components[retained],
            policy=negative_policy,
            tolerance=negative_tolerance,
            label="Per-atom velocity spectrum",
        )
        per_atom = np.sum(per_atom_components, axis=2, dtype=np.float64)
        per_atom_indices = np.array(
            spectrum.per_atom_indices, dtype=np.int64, copy=True
        )

    integrated_before = float(spectral_bin_integral(total, frequencies))
    if not np.isfinite(integrated_before) or integrated_before <= 0.0:
        raise ValueError(
            "The retained nonnegative spectral weight must be finite and positive."
        )

    factor = 1.0 if target is None else float(target) / integrated_before
    total *= factor
    components *= factor
    if per_atom is not None:
        per_atom *= factor
        per_atom_components *= factor
    integrated_after = float(spectral_bin_integral(total, frequencies))

    _, wavenumbers, energies = convert_frequency_axes(frequencies)
    if normalization == "none":
        density_units = spectrum.spectrum_units
    elif normalization == "unit_area":
        density_units = "1/THz"
    else:
        density_units = "degrees_of_freedom/THz"

    metadata: dict[str, Any] = {
        "source_normalization": spectrum.normalization,
        "source_correlation_weighting": spectrum.correlation_weighting,
        "source_spectral_sidedness": spectrum.spectral_sidedness,
        "source_spectral_scaling": spectrum.spectral_scaling,
        "source_spectrum_units": spectrum.spectrum_units,
        "source_n_fft": spectrum.n_fft,
        "source_sample_spacing_ps": spectrum.sample_spacing_ps,
        "source_frequency_count": int(spectrum.frequencies_thz.size),
        "first_retained_bin": first_retained,
        "retained_frequency_count": int(frequencies.size),
        "minimum_frequency_thz": threshold,
        "negative_policy": negative_policy,
        "negative_tolerance": float(negative_tolerance),
        "normalization_factor": float(factor),
        "interpretation": (
            "mass_weighted_vdos"
            if spectrum.weighting == "mass"
            else "velocity_derived_vdos"
        ),
        "phonon_dos_claimed": False,
        "two_phase_thermodynamics": False,
        "source_metadata": dict(spectrum.metadata),
    }

    return VDOSResult(
        frequencies_thz=frequencies,
        wavenumbers_cm_inv=wavenumbers,
        energies_mev=energies,
        total=total,
        components=components,
        per_atom=per_atom,
        per_atom_components=per_atom_components,
        per_atom_indices=per_atom_indices,
        normalization=normalization,
        integrated_weight_before=integrated_before,
        integrated_weight_after=integrated_after,
        target_weight=target,
        source_estimator=spectrum.estimator,
        weighting=spectrum.weighting,
        density_units=density_units,
        metadata=metadata,
        signature=spectrum.signature,
    )
