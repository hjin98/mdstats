"""Periodic coordinate conversion and unwrapping."""

from __future__ import annotations

import warnings

import numpy as np
from numpy.typing import NDArray

from ..exceptions import CoordinateFormatError, InvalidCellError
from ..io.common import CoordinateKind


class UnwrappingWarning(UserWarning):
    """Warning emitted when inferred image reconstruction is ambiguous."""


def cartesian_to_fractional(
    cartesian: NDArray[np.float64],
    cells: NDArray[np.float64],
    origins: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Convert frame-dependent Cartesian coordinates to row-vector fractions."""
    shifted = np.asarray(cartesian, dtype=np.float64) - origins[:, None, :]
    try:
        inverse_cells = np.linalg.inv(cells)
    except np.linalg.LinAlgError as exc:
        raise InvalidCellError("Cannot invert one or more simulation cells.") from exc
    return np.einsum("tni,tij->tnj", shifted, inverse_cells, optimize=True)


def infer_unwrapped_fractional_positions(
    wrapped_fractional: NDArray[np.float64],
    pbc: NDArray[np.bool_],
    *,
    warning_threshold: float = 0.45,
) -> NDArray[np.float64]:
    """Infer a continuous fractional trajectory by minimum-image increments.

    The operation is exact only when every saved-frame displacement is smaller
    than half a periodic cell span along each fractional direction.
    """
    wrapped = np.array(wrapped_fractional, dtype=np.float64, copy=True)
    if wrapped.ndim != 3 or wrapped.shape[-1] != 3:
        raise CoordinateFormatError(
            "Wrapped fractional coordinates must have shape (T, N, 3)."
        )

    for axis, periodic in enumerate(pbc):
        if periodic:
            wrapped[..., axis] -= np.floor(wrapped[..., axis])

    result = np.empty_like(wrapped)
    result[0] = wrapped[0]
    if wrapped.shape[0] == 1:
        return result

    delta = np.diff(wrapped, axis=0)
    for axis, periodic in enumerate(pbc):
        if periodic:
            delta[..., axis] -= np.rint(delta[..., axis])
            maximum = float(np.max(np.abs(delta[..., axis])))
            if maximum > warning_threshold:
                warnings.warn(
                    "Minimum-image unwrapping encountered a fractional "
                    f"displacement of {maximum:.6g} along axis {axis}. "
                    "The saved-frame interval may be too large to identify "
                    "the correct periodic image uniquely.",
                    UnwrappingWarning,
                    stacklevel=2,
                )

    result[1:] = result[0] + np.cumsum(delta, axis=0)
    return result


def construct_unwrapped_fractional_positions(
    *,
    coordinate_kind: CoordinateKind,
    coordinates: NDArray[np.float64],
    cells: NDArray[np.float64],
    origins: NDArray[np.float64],
    pbc: NDArray[np.bool_],
    image_flags: NDArray[np.int64] | None,
    warning_threshold: float = 0.45,
) -> tuple[NDArray[np.float64], str]:
    """Normalize source coordinates to unwrapped fractional coordinates.

    Returns
    -------
    positions, method
        The continuous fractional trajectory and a provenance method string.
    """
    coordinates = np.asarray(coordinates, dtype=np.float64)

    if coordinate_kind == "unwrapped_fractional":
        return coordinates.copy(), "native_unwrapped_fractional"

    if coordinate_kind == "unwrapped_cartesian":
        scaled = cartesian_to_fractional(coordinates, cells, origins)
        return scaled, "native_unwrapped_cartesian"

    if coordinate_kind == "wrapped_fractional":
        wrapped = coordinates.copy()
    elif coordinate_kind == "wrapped_cartesian":
        wrapped = cartesian_to_fractional(coordinates, cells, origins)
    else:  # Defensive; CoordinateKind is statically constrained.
        raise CoordinateFormatError(f"Unsupported coordinate kind {coordinate_kind!r}.")

    for axis, periodic in enumerate(pbc):
        if periodic:
            wrapped[..., axis] -= np.floor(wrapped[..., axis])

    if image_flags is not None:
        images = np.asarray(image_flags, dtype=np.int64)
        if images.shape != wrapped.shape:
            raise CoordinateFormatError(
                "Image flags must have the same shape as atomic coordinates."
            )
        result = wrapped.copy()
        for axis, periodic in enumerate(pbc):
            if periodic:
                result[..., axis] += images[..., axis]
        return result, "image_flags"

    return (
        infer_unwrapped_fractional_positions(
            wrapped, pbc, warning_threshold=warning_threshold
        ),
        "minimum_image_inferred",
    )


def construct_independent_fractional_positions(
    *,
    coordinate_kind: CoordinateKind,
    coordinates: NDArray[np.float64],
    cells: NDArray[np.float64],
    origins: NDArray[np.float64],
    pbc: NDArray[np.bool_],
) -> tuple[NDArray[np.float64], str]:
    """Normalize independent frames without inferring cross-frame continuity.

    Cartesian inputs are converted with each frame's own cell and origin. Every
    periodic fractional component is then wrapped into ``[0, 1)``. Image flags
    and unwrapped source coordinates are intentionally reduced because an
    ensemble has no meaningful periodic image continuity between frames.
    """
    coordinates = np.asarray(coordinates, dtype=np.float64)
    if coordinate_kind.endswith("fractional"):
        scaled = coordinates.copy()
    elif coordinate_kind.endswith("cartesian"):
        scaled = cartesian_to_fractional(coordinates, cells, origins)
    else:  # defensive
        raise CoordinateFormatError(f"Unsupported coordinate kind {coordinate_kind!r}.")

    for axis, periodic in enumerate(pbc):
        if periodic:
            scaled[..., axis] -= np.floor(scaled[..., axis])
    return scaled, "independent_frame_wrapping"
