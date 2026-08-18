"""Internal spectral transforms for uniformly sampled correlation functions.

The module complements :mod:`mdstats.analysis._fft`.  ``_fft.py`` constructs
linear positive-lag correlations from time series, whereas this module turns a
stored positive-lag correlation into a one-sided spectral density. It also
provides the memory-aware atom-block plan used by direct spectral estimators.

The autocorrelation/spectral-density relation follows the Wiener-Khinchin
lineage [Wiener, 1930, DOI: 10.1007/BF02546511; Khintchine, 1934, DOI:
10.1007/BF01449156]. Window trade-offs follow Harris (1978), DOI:
10.1109/PROC.1978.10837. The positive-lag tensor layout, explicit half-window
API, and one-sided density metadata are mdstats implementation choices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
from numpy.exceptions import AxisError
from numpy.typing import ArrayLike, NDArray
from scipy.fft import next_fast_len, rfft, rfftfreq

FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
LagWindowInput: TypeAlias = str | tuple[str, float] | ArrayLike


@dataclass(frozen=True, slots=True)
class AtomSpectrumPlan:
    """Memory-aware atom-block plan for direct spectral estimators."""

    n_fft: int
    n_frequency: int
    atom_block_size: int
    estimated_work_bytes: int


def _require_positive_integer(value: object, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise TypeError(f"{name} must be an integer.")
    resolved = int(value)
    if resolved < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return resolved


def make_atom_spectrum_plan(
    n_atoms: int,
    segment_length: int,
    n_fft: int,
    *,
    atom_block_size: int | None,
    memory_target_bytes: int,
) -> AtomSpectrumPlan:
    """Plan atom blocking for a direct real-input spectral transform.

    The estimate counts, per atom, one Cartesian input segment, one padded
    real work array, one three-component complex RFFT, and one real diagonal
    periodogram scratch array.  It intentionally excludes estimator-wide
    accumulators and opaque backend work buffers.  The model adapts the
    existing mdstats ``make_atom_fft_plan`` architecture; it is not a borrowed
    external algorithm.
    """

    resolved_atoms = _require_positive_integer(n_atoms, name="n_atoms")
    resolved_segment = _require_positive_integer(
        segment_length, name="segment_length"
    )
    resolved_n_fft = _require_positive_integer(n_fft, name="n_fft")
    if resolved_n_fft < resolved_segment:
        raise ValueError("n_fft must be greater than or equal to segment_length.")
    resolved_target = _require_positive_integer(
        memory_target_bytes, name="memory_target_bytes"
    )

    n_frequency = resolved_n_fft // 2 + 1
    real_itemsize = np.dtype(np.float64).itemsize
    complex_itemsize = np.dtype(np.complex128).itemsize
    bytes_per_atom = (
        3 * resolved_segment * real_itemsize
        + 3 * resolved_n_fft * real_itemsize
        + 3 * n_frequency * complex_itemsize
        + 3 * n_frequency * real_itemsize
    )

    if atom_block_size is None:
        resolved_block = max(
            1,
            min(resolved_atoms, resolved_target // max(1, bytes_per_atom)),
        )
    else:
        requested_block = _require_positive_integer(
            atom_block_size, name="atom_block_size"
        )
        resolved_block = min(resolved_atoms, requested_block)

    return AtomSpectrumPlan(
        n_fft=resolved_n_fft,
        n_frequency=n_frequency,
        atom_block_size=int(resolved_block),
        estimated_work_bytes=int(resolved_block * bytes_per_atom),
    )


def resolve_spectrum_fft_length(
    n_positive_lags: int,
    *,
    zero_pad_to: int | None,
) -> int:
    """Return a fast transform length for a positive-lag correlation.

    A correlation containing ``L`` nonnegative lags requires at least
    ``2 * L - 1`` samples to hold lag zero, all positive lags, and all negative
    lags without overlap.  ``zero_pad_to`` is an optional lower bound on the
    work-array length; it refines the frequency grid but does not improve the
    physical frequency resolution.
    """

    n_lags = _require_positive_integer(
        n_positive_lags, name="n_positive_lags"
    )
    lower_bound = 2 * n_lags - 1
    if zero_pad_to is not None:
        lower_bound = max(
            lower_bound,
            _require_positive_integer(zero_pad_to, name="zero_pad_to"),
        )
    return int(next_fast_len(lower_bound))


def resolve_lag_window(
    window: LagWindowInput | None,
    n_lags: int,
) -> tuple[FloatArray, dict[str, Any]]:
    """Resolve a zero-centered positive-lag taper.

    Built-in windows always satisfy ``w[0] == 1``.  This is essential for a
    VACF: applying an ordinary full Hann array directly would erase the
    lag-zero correlation.  ``half_tukey`` uses ``alpha`` as the fraction of
    the positive-lag interval occupied by the terminal cosine taper.
    """

    length = _require_positive_integer(n_lags, name="n_lags")

    if window is None:
        values = np.ones(length, dtype=np.float64)
        return values, {"name": None, "kind": "rectangular", "alpha": None}

    if isinstance(window, str):
        name = window.lower()
        parameter: float | None = None
    elif isinstance(window, tuple):
        if len(window) != 2 or not isinstance(window[0], str):
            raise ValueError(
                "A parameterized lag window must be a (name, parameter) tuple."
            )
        name = window[0].lower()
        parameter = float(window[1])
    else:
        values = np.asarray(window, dtype=np.float64)
        if values.shape != (length,):
            raise ValueError(
                f"Custom lag window has shape {values.shape}; expected ({length},)."
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("Custom lag window must contain only finite values.")
        if not np.isclose(values[0], 1.0, rtol=0.0, atol=1.0e-12):
            raise ValueError("Custom lag window must satisfy window[0] == 1.")
        return np.array(values, dtype=np.float64, copy=True), {
            "name": "custom",
            "kind": "custom",
            "alpha": None,
            "values": values.tolist(),
        }

    if name == "half_hann":
        if parameter is not None:
            raise ValueError("half_hann does not accept a parameter.")
        if length == 1:
            values = np.ones(1, dtype=np.float64)
        else:
            x = np.arange(length, dtype=np.float64) / float(length - 1)
            values = 0.5 * (1.0 + np.cos(np.pi * x))
        return values, {"name": "half_hann", "kind": "half_hann", "alpha": 1.0}

    if name == "half_tukey":
        if parameter is None:
            raise ValueError("half_tukey requires an alpha parameter.")
        alpha = float(parameter)
        if not np.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
            raise ValueError("half_tukey alpha must lie in the closed interval [0, 1].")
        if length == 1 or alpha == 0.0:
            values = np.ones(length, dtype=np.float64)
        else:
            x = np.arange(length, dtype=np.float64) / float(length - 1)
            values = np.ones(length, dtype=np.float64)
            start = 1.0 - alpha
            taper = x > start
            values[taper] = 0.5 * (
                1.0 + np.cos(np.pi * (x[taper] - start) / alpha)
            )
        return values, {
            "name": "half_tukey",
            "kind": "half_tukey",
            "alpha": alpha,
        }

    raise ValueError(
        "window must be None, 'half_hann', ('half_tukey', alpha), or a custom array."
    )


def reconstruct_two_sided_correlation(
    positive_lag: ArrayLike,
    *,
    n_fft: int,
    tensor_axes: tuple[int, int] | None = None,
) -> FloatArray:
    """Embed a positive-lag correlation in a real periodic work array.

    The lag axis is axis zero.  Without ``tensor_axes``, negative lags are the
    reversed positive-lag values.  With tensor axes ``(a, b)``, stationarity
    requires ``C_ab(-t) = C_ba(t)``, so the negative-lag block is additionally
    transposed along those axes.
    """

    values = np.asarray(positive_lag, dtype=np.float64)
    if values.ndim < 1:
        raise ValueError("positive_lag must have at least one dimension.")
    if values.shape[0] < 1:
        raise ValueError("positive_lag must contain lag zero.")
    if not np.all(np.isfinite(values)):
        raise ValueError("positive_lag must contain only finite values.")

    resolved_n_fft = _require_positive_integer(n_fft, name="n_fft")
    n_lags = int(values.shape[0])
    minimum = 2 * n_lags - 1
    if resolved_n_fft < minimum:
        raise ValueError(
            f"n_fft={resolved_n_fft} is too small for {n_lags} nonnegative lags; "
            f"at least {minimum} is required."
        )

    resolved_axes: tuple[int, int] | None = None
    if tensor_axes is not None:
        if len(tensor_axes) != 2:
            raise ValueError("tensor_axes must contain exactly two axes.")
        axis_a = int(tensor_axes[0])
        axis_b = int(tensor_axes[1])
        if axis_a < 0:
            axis_a += values.ndim
        if axis_b < 0:
            axis_b += values.ndim
        if axis_a == 0 or axis_b == 0:
            raise ValueError("tensor_axes must not include the lag axis zero.")
        if axis_a == axis_b or not (0 <= axis_a < values.ndim) or not (
            0 <= axis_b < values.ndim
        ):
            raise ValueError("tensor_axes must be distinct valid array axes.")
        if values.shape[axis_a] != values.shape[axis_b]:
            raise ValueError("tensor_axes must have equal lengths.")
        resolved_axes = (axis_a, axis_b)

    work = np.zeros((resolved_n_fft, *values.shape[1:]), dtype=np.float64)
    work[:n_lags] = values
    if n_lags > 1:
        negative = values[1:]
        if resolved_axes is not None:
            negative = np.swapaxes(negative, resolved_axes[0], resolved_axes[1])
        work[resolved_n_fft - n_lags + 1 :] = negative[::-1]
    return work


def one_sided_density_scale(n_fft: int) -> FloatArray:
    """Return the real-input one-sided density scale for an FFT length."""

    resolved = _require_positive_integer(n_fft, name="n_fft")
    n_frequency = resolved // 2 + 1
    scale = np.ones(n_frequency, dtype=np.float64)
    if resolved % 2 == 0:
        if n_frequency > 2:
            scale[1:-1] = 2.0
    elif n_frequency > 1:
        scale[1:] = 2.0
    return scale


def transform_positive_lag_correlation(
    correlation: ArrayLike,
    *,
    dt_ps: float,
    n_fft: int,
    tensor_axes: tuple[int, int] | None = None,
) -> tuple[FloatArray, ComplexArray]:
    """Transform a positive-lag correlation into a one-sided density.

    The Wiener-Khinchin relation supplies the physical connection between a
    stationary correlation and its spectrum.  Numerically, mdstats performs a
    real two-sided reconstruction, an ``rfft``, multiplication by ``dt_ps`` to
    approximate the continuous-time transform, and standard one-sided density
    scaling.
    """

    if not np.isfinite(dt_ps) or dt_ps <= 0.0:
        raise ValueError("dt_ps must be finite and strictly positive.")
    resolved_n_fft = _require_positive_integer(n_fft, name="n_fft")
    work = reconstruct_two_sided_correlation(
        correlation,
        n_fft=resolved_n_fft,
        tensor_axes=tensor_axes,
    )
    transformed = np.asarray(
        rfft(work, n=resolved_n_fft, axis=0), dtype=np.complex128
    )
    transformed *= float(dt_ps)
    scale = one_sided_density_scale(resolved_n_fft)
    transformed *= scale.reshape((scale.size,) + (1,) * (transformed.ndim - 1))
    frequencies = np.asarray(
        rfftfreq(resolved_n_fft, d=float(dt_ps)), dtype=np.float64
    )
    return frequencies, transformed



def spectral_bin_integral(
    spectrum: ArrayLike,
    frequencies_thz: ArrayLike,
    *,
    axis: int = 0,
) -> FloatArray | np.float64:
    """Integrate a one-sided spectral density by its uniform FFT-bin measure.

    The stored one-sided spectrum already includes the DC/interior/Nyquist
    bookkeeping applied by :func:`one_sided_density_scale`.  Its normative
    discrete total is therefore ``df * sum(P_m)`` rather than a trapezoidal
    endpoint approximation to an interpolated curve.  This convention is an
    mdstats numerical contract, not a new quadrature algorithm.
    """

    if np.iscomplexobj(spectrum):
        raise TypeError("spectrum must be real; complex values are not supported.")
    values = np.asarray(spectrum, dtype=np.float64)
    if values.ndim == 0:
        raise ValueError("spectrum must have at least one dimension.")
    if isinstance(axis, (bool, np.bool_)) or not isinstance(
        axis, (int, np.integer)
    ):
        raise TypeError("axis must be an integer.")
    resolved_axis = int(axis)
    if resolved_axis < 0:
        resolved_axis += values.ndim
    if resolved_axis < 0 or resolved_axis >= values.ndim:
        raise AxisError(axis, ndim=values.ndim)

    frequencies = np.asarray(frequencies_thz, dtype=np.float64)
    if frequencies.ndim != 1:
        raise ValueError("frequencies_thz must be one-dimensional.")
    if frequencies.size < 2:
        raise ValueError("frequencies_thz must contain at least two bins.")
    if values.shape[resolved_axis] != frequencies.size:
        raise ValueError(
            "The frequency count does not match the spectrum-axis length: "
            f"{frequencies.size} != {values.shape[resolved_axis]}."
        )
    if not np.all(np.isfinite(values)):
        raise ValueError("spectrum must contain only finite values.")
    if not np.all(np.isfinite(frequencies)):
        raise ValueError("frequencies_thz must contain only finite values.")
    if frequencies[0] < 0.0:
        raise ValueError("frequencies_thz must be nonnegative.")

    increments = np.diff(frequencies)
    if np.any(increments <= 0.0):
        raise ValueError("frequencies_thz must be strictly increasing.")
    spacing = float(increments[0])
    if not np.allclose(
        increments,
        spacing,
        rtol=1.0e-12,
        atol=max(1.0e-14, 1.0e-12 * abs(spacing)),
    ):
        raise ValueError("frequencies_thz must be uniformly spaced.")

    integrated = spacing * np.sum(values, axis=resolved_axis, dtype=np.float64)
    result = np.asarray(integrated, dtype=np.float64)
    if result.ndim == 0:
        return np.float64(result)
    return result
