"""Shared FFT planning and linear-correlation helpers.

The public analysis modules keep their estimator-specific algebra.  This
module centralizes only the numerical machinery that should be identical
between VACF, MSD, and future time-correlation routines: zero-padding,
positive-lag linear correlation, and memory-aware atom blocking.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.fft import irfft, next_fast_len

FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]


@dataclass(frozen=True, slots=True)
class AtomFFTPlan:
    """FFT length and atom-block size for one time-series calculation."""

    n_fft: int
    n_frequency: int
    atom_block_size: int


def linear_fft_length(n_samples: int) -> int:
    """Return a fast FFT length for a non-circular correlation.

    Zero-padding to at least ``2 * n_samples - 1`` ensures that the inverse
    transform contains the desired linear correlation rather than a wrapped
    circular correlation.
    """
    if not isinstance(n_samples, (int, np.integer)) or n_samples < 1:
        raise ValueError("n_samples must be a positive integer.")
    return int(next_fast_len(2 * int(n_samples) - 1))


def positive_lag_pair_counts(n_samples: int, max_lag: int) -> FloatArray:
    """Return the number of valid all-origin pairs at each positive lag."""
    if not isinstance(n_samples, (int, np.integer)) or n_samples < 1:
        raise ValueError("n_samples must be a positive integer.")
    if not isinstance(max_lag, (int, np.integer)):
        raise TypeError("max_lag must be an integer.")
    n_samples = int(n_samples)
    max_lag = int(max_lag)
    if max_lag < 0 or max_lag >= n_samples:
        raise ValueError("max_lag must lie in 0..n_samples-1.")
    return np.arange(n_samples, n_samples - max_lag - 1, -1, dtype=np.float64)


def make_atom_fft_plan(
    n_atoms: int,
    n_frames: int,
    *,
    atom_block_size: int | None = None,
    memory_target_bytes: int = 256 * 1024 * 1024,
    real_series_per_atom: int = 3,
    complex_series_per_atom: int = 3,
    inverse_real_series_per_atom: int = 3,
) -> AtomFFTPlan:
    """Construct a conservative memory-aware plan for atom-blocked FFTs.

    The series counts describe the largest temporary workspace expected per
    atom.  They are deliberately explicit so different estimators can share
    the planning logic without hiding estimator-specific arrays here.
    """
    for name, value in (("n_atoms", n_atoms), ("n_frames", n_frames)):
        if not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer.")
    if (
        not isinstance(memory_target_bytes, (int, np.integer))
        or memory_target_bytes < 1
    ):
        raise ValueError("memory_target_bytes must be a positive integer.")
    for name, value in (
        ("real_series_per_atom", real_series_per_atom),
        ("complex_series_per_atom", complex_series_per_atom),
        ("inverse_real_series_per_atom", inverse_real_series_per_atom),
    ):
        if not isinstance(value, (int, np.integer)) or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer.")

    n_atoms = int(n_atoms)
    n_frames = int(n_frames)
    n_fft = linear_fft_length(n_frames)
    n_frequency = n_fft // 2 + 1

    if atom_block_size is not None:
        if not isinstance(atom_block_size, (int, np.integer)) or atom_block_size < 1:
            raise ValueError("atom_block_size must be a positive integer or None.")
        resolved = min(int(atom_block_size), n_atoms)
    else:
        bytes_per_atom = (
            int(real_series_per_atom) * n_frames * np.dtype(np.float64).itemsize
            + int(complex_series_per_atom)
            * n_frequency
            * np.dtype(np.complex128).itemsize
            + int(inverse_real_series_per_atom) * n_fft * np.dtype(np.float64).itemsize
        )
        resolved = max(
            1,
            min(
                n_atoms,
                int(memory_target_bytes) // max(1, bytes_per_atom),
            ),
        )

    return AtomFFTPlan(
        n_fft=n_fft,
        n_frequency=n_frequency,
        atom_block_size=resolved,
    )


def positive_lag_correlation_from_spectrum(
    cross_spectrum: ComplexArray,
    *,
    n_fft: int,
    max_lag: int,
) -> FloatArray:
    """Invert a cross spectrum and return its linear positive-lag sums.

    The input spectrum must follow ``conj(FFT(x)) * FFT(y)``.  The returned
    value at lag ``k`` is therefore ``sum_n x[n] * y[n + k]`` before any
    division by the number of contributing origins.
    """
    spectrum = np.asarray(cross_spectrum, dtype=np.complex128)
    if spectrum.shape[-1] != n_fft // 2 + 1:
        raise ValueError(
            "cross_spectrum has an incompatible frequency-axis length for n_fft."
        )
    if max_lag < 0 or max_lag >= n_fft:
        raise ValueError("max_lag must be nonnegative and smaller than n_fft.")
    return np.asarray(irfft(spectrum, n=n_fft, axis=-1)[..., : max_lag + 1])
