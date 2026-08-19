"""Frequency-axis conversions for dynamical spectra.

The canonical mdstats spectral frequency is cycles per picosecond, numerically
identical to THz.  Other axes are deterministic unit conversions and do not
represent separately sampled spectra.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.constants import c, electron_volt, h

FloatArray = NDArray[np.float64]


def convert_frequency_axes(
    frequencies_thz: ArrayLike,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Return angular frequency, wavenumber, and energy axes.

    Returns
    -------
    angular_frequencies_ps_inv
        Angular frequency in rad/ps.
    wavenumbers_cm_inv
        Spectroscopic wavenumber in cm^-1.
    energies_mev
        Quantum energy ``h f`` in meV.
    """

    frequencies = np.asarray(frequencies_thz, dtype=np.float64)
    if frequencies.ndim != 1:
        raise ValueError("frequencies_thz must be one-dimensional.")
    if frequencies.size < 1:
        raise ValueError("frequencies_thz must not be empty.")
    if not np.all(np.isfinite(frequencies)) or np.any(frequencies < 0.0):
        raise ValueError("frequencies_thz must be finite and nonnegative.")

    angular = 2.0 * np.pi * frequencies
    wavenumber = frequencies * 1.0e12 / (c * 100.0)
    energy = frequencies * (h * 1.0e15 / electron_volt)
    return (
        np.asarray(angular, dtype=np.float64),
        np.asarray(wavenumber, dtype=np.float64),
        np.asarray(energy, dtype=np.float64),
    )
