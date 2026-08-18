"""Validated sampled-data quadrature primitives.

The composite trapezoidal rule is standard numerical-analysis machinery.  The
implementation delegates the arithmetic to
:func:`scipy.integrate.cumulative_trapezoid` [Virtanen et al., Nature Methods
17, 261-272 (2020), DOI: 10.1038/s41592-019-0686-2].  mdstats adds the strict
finite, shape, monotonicity, dtype, and length-preserving contract used by
correlation-function transport analyses.
"""

from __future__ import annotations

import numpy as np
from numpy.exceptions import AxisError
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import cumulative_trapezoid

FloatArray = NDArray[np.float64]


def _normalize_axis(axis: int, ndim: int) -> int:
    """Return a nonnegative axis index with a stable public error contract."""
    if isinstance(axis, (bool, np.bool_)) or not isinstance(axis, (int, np.integer)):
        raise TypeError("axis must be an integer.")
    resolved = int(axis)
    if resolved < 0:
        resolved += ndim
    if resolved < 0 or resolved >= ndim:
        raise AxisError(axis, ndim=ndim)
    return resolved


def cumulative_trapezoid_zero(
    values: ArrayLike,
    coordinates: ArrayLike,
    *,
    axis: int = 0,
) -> FloatArray:
    """Cumulatively integrate sampled values with a leading exact zero.

    Parameters
    ----------
    values
        Finite sampled values.  The integration axis may be any array axis.
    coordinates
        One-dimensional finite coordinates for the integration axis.  They
        must be strictly increasing and have the same length as that axis.
    axis
        Axis of ``values`` corresponding to ``coordinates``.

    Returns
    -------
    numpy.ndarray
        A ``float64`` array with the same shape as ``values``.  The first
        sample along ``axis`` is exactly zero.

    Notes
    -----
    This is a validated wrapper around SciPy's composite cumulative
    trapezoidal rule.  It intentionally does not interpolate, smooth, sort,
    deduplicate, or extrapolate the sampled data.
    """
    sampled = np.asarray(values, dtype=np.float64)
    if sampled.ndim == 0:
        raise ValueError("values must have at least one dimension.")
    resolved_axis = _normalize_axis(axis, sampled.ndim)

    x = np.asarray(coordinates, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("coordinates must be one-dimensional.")
    if x.size < 1:
        raise ValueError("coordinates must contain at least one sample.")
    if sampled.shape[resolved_axis] != x.size:
        raise ValueError(
            "The coordinate count does not match the integration-axis length: "
            f"{x.size} != {sampled.shape[resolved_axis]}."
        )
    if not np.all(np.isfinite(sampled)):
        raise ValueError("values must contain only finite samples.")
    if not np.all(np.isfinite(x)):
        raise ValueError("coordinates must contain only finite samples.")
    if x.size > 1 and np.any(np.diff(x) <= 0.0):
        raise ValueError("coordinates must be strictly increasing.")

    # The quadrature arithmetic is SciPy's cumulative composite trapezoidal
    # rule.  mdstats fixes initial=0.0 so callers receive a length-preserving
    # running integral aligned exactly with the input sampling grid.
    integrated = cumulative_trapezoid(
        sampled,
        x=x,
        axis=resolved_axis,
        initial=0.0,
    )
    result = np.asarray(integrated, dtype=np.float64)

    first = [slice(None)] * result.ndim
    first[resolved_axis] = 0
    result[tuple(first)] = 0.0
    return result
