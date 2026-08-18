"""Velocity validation and finite-difference reconstruction."""

from __future__ import annotations

import warnings

import numpy as np
from numpy.typing import NDArray

from ..exceptions import MissingTimeError


class VelocityReconstructionWarning(UserWarning):
    """Warning emitted for low-order or potentially noisy velocity recovery."""


def reconstruct_velocities(
    cartesian_positions: NDArray[np.float64],
    times: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Reconstruct Cartesian velocities from continuous positions.

    ``numpy.gradient`` supplies second-order centered differences internally
    and second-order one-sided differences at the endpoints.  It also supports
    nonuniform frame times.  With exactly two frames only a first-order slope
    is possible and is assigned to both frames.
    """
    positions = np.asarray(cartesian_positions, dtype=np.float64)
    times = np.asarray(times, dtype=np.float64)
    n_frames = positions.shape[0]

    if n_frames < 2:
        raise MissingTimeError(
            "At least two position frames are required to reconstruct velocities."
        )
    if times.shape != (n_frames,):
        raise MissingTimeError(
            "The time array does not match the number of position frames."
        )
    if not np.all(np.diff(times) > 0.0):
        raise MissingTimeError(
            "Frame times must be strictly increasing for finite differences."
        )

    if n_frames == 2:
        slope = (positions[1] - positions[0]) / (times[1] - times[0])
        warnings.warn(
            "Only two frames are available; assigning the same first-order "
            "finite-difference velocity to both frames.",
            VelocityReconstructionWarning,
            stacklevel=2,
        )
        return np.stack((slope, slope), axis=0)

    return np.asarray(
        np.gradient(positions, times, axis=0, edge_order=2),
        dtype=np.float64,
    )
