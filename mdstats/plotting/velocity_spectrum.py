"""Plotting helpers for velocity spectra and normalized VDOS results.

Rendering is delegated to Matplotlib [Hunter, Comput. Sci. Eng. 9, 90-95
(2007), DOI: 10.1109/MCSE.2007.55]. The result-type distinction, bounded
per-atom guard, common display-normalization scale, axis-label contract, and
preservation of THz-based ordinate units are mdstats design decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np

from ..analysis.velocity_spectrum import VDOSResult, VelocitySpectrumResult

SpectrumPlotResult = VelocitySpectrumResult | VDOSResult
SpectrumXAxis = Literal["thz", "cm^-1", "mev"]
SpectrumProjection = Literal["total", "components", "per_atom"]

_MAX_IMPLICIT_PER_ATOM_CURVES = 12


def _axis_values_and_label(
    result: SpectrumPlotResult,
    x_axis: SpectrumXAxis,
) -> tuple[np.ndarray, str]:
    """Return the stored horizontal coordinate and its display label."""
    if x_axis == "thz":
        return np.asarray(result.frequencies_thz, dtype=np.float64), "Frequency (THz)"
    if x_axis == "cm^-1":
        return (
            np.asarray(result.wavenumbers_cm_inv, dtype=np.float64),
            r"Wavenumber ($\mathrm{cm}^{-1}$)",
        )
    if x_axis == "mev":
        return np.asarray(result.energies_mev, dtype=np.float64), "Energy (meV)"
    raise ValueError("x_axis must be 'thz', 'cm^-1', or 'mev'.")


def _format_units(units: str) -> str:
    """Return a compact Matplotlib label for known spectral-density units."""
    known = {
        "Å^2/ps": r"$\mathrm{\AA}^2/\mathrm{ps}$",
        "amu*Å^2/ps": r"$\mathrm{amu}\,\mathrm{\AA}^2/\mathrm{ps}$",
        "1/THz": r"$\mathrm{THz}^{-1}$",
        "degrees_of_freedom/THz": r"degrees of freedom / THz",
    }
    return known.get(units, units)


def _ordinate_label(
    result: SpectrumPlotResult,
    *,
    normalize_for_display: bool,
) -> str:
    """Return the result-aware vertical-axis label."""
    if normalize_for_display:
        return "Display-normalized intensity (arb. units)"
    if isinstance(result, VelocitySpectrumResult):
        return f"Velocity spectral density ({_format_units(result.spectrum_units)})"
    return f"VDOS ({_format_units(result.density_units)})"


def _resolve_atom_columns(
    available_indices: np.ndarray,
    atom_indices: Sequence[int] | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Resolve requested canonical atom indices to per-atom result columns."""
    available = np.asarray(available_indices, dtype=np.int64)
    if atom_indices is None:
        if available.size > _MAX_IMPLICIT_PER_ATOM_CURVES:
            raise ValueError(
                "Per-atom plotting would create "
                f"{available.size} curves. Pass atom_indices explicitly when more "
                f"than {_MAX_IMPLICIT_PER_ATOM_CURVES} per-atom curves are stored."
            )
        return available.copy(), np.arange(available.size, dtype=np.int64)

    requested_raw = np.asarray(atom_indices)
    if requested_raw.ndim != 1:
        raise ValueError("atom_indices must be one-dimensional.")
    if requested_raw.size == 0:
        raise ValueError("atom_indices must not be empty.")
    if np.issubdtype(requested_raw.dtype, np.bool_) or not np.issubdtype(
        requested_raw.dtype, np.integer
    ):
        raise TypeError("atom_indices must contain integers.")

    requested = requested_raw.astype(np.int64, copy=False)
    if np.unique(requested).size != requested.size:
        raise ValueError("atom_indices must not contain duplicates.")

    lookup = {int(atom_id): column for column, atom_id in enumerate(available)}
    missing = [int(atom_id) for atom_id in requested if int(atom_id) not in lookup]
    if missing:
        raise ValueError(
            f"Requested atom indices are absent from the stored per-atom data: {missing}."
        )
    columns = np.asarray([lookup[int(atom_id)] for atom_id in requested], dtype=np.int64)
    return requested.copy(), columns


def _plot_curves(
    result: SpectrumPlotResult,
    *,
    projection: SpectrumProjection,
    atom_indices: Sequence[int] | None,
) -> tuple[np.ndarray, list[str]]:
    """Return a ``(frequency, curve)`` matrix and deterministic curve labels."""
    if projection == "total":
        if atom_indices is not None:
            raise ValueError("atom_indices is only valid for projection='per_atom'.")
        values = (
            result.scalar_spectrum
            if isinstance(result, VelocitySpectrumResult)
            else result.total
        )
        return np.asarray(values, dtype=np.float64)[:, None], ["Total"]

    if projection == "components":
        if atom_indices is not None:
            raise ValueError("atom_indices is only valid for projection='per_atom'.")
        values = (
            result.component_spectra
            if isinstance(result, VelocitySpectrumResult)
            else result.components
        )
        return np.asarray(values, dtype=np.float64), [r"$x$", r"$y$", r"$z$"]

    if projection != "per_atom":
        raise ValueError("projection must be 'total', 'components', or 'per_atom'.")

    if isinstance(result, VelocitySpectrumResult):
        per_atom = result.per_atom_scalar
        stored_indices = result.per_atom_indices
    else:
        per_atom = result.per_atom
        stored_indices = result.per_atom_indices

    if per_atom is None or stored_indices is None:
        raise ValueError(
            "Per-atom spectral data are unavailable. Recompute the source VACF "
            "and spectrum with per-atom output enabled."
        )

    selected_ids, columns = _resolve_atom_columns(stored_indices, atom_indices)
    values = np.asarray(per_atom, dtype=np.float64)[:, columns]
    labels = [f"Atom {int(atom_id)}" for atom_id in selected_ids]
    return values, labels


def plot_velocity_spectrum(
    result: SpectrumPlotResult,
    *,
    x_axis: SpectrumXAxis = "thz",
    projection: SpectrumProjection = "total",
    atom_indices: Sequence[int] | None = None,
    normalize_for_display: bool = False,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Plot a velocity spectral density or normalized VDOS result.

    Parameters
    ----------
    result
        A :class:`~mdstats.analysis.velocity_spectrum.VelocitySpectrumResult`
        or :class:`~mdstats.analysis.velocity_spectrum.VDOSResult`.
    x_axis
        Stored horizontal coordinate to display: frequency in THz, wavenumber
        in inverse centimeters, or energy in meV. Changing the horizontal
        coordinate does not apply a Jacobian to the ordinate; scientific
        density units remain those stored by ``result`` and remain normalized
        with respect to the THz grid.
    projection
        Plot the total scalar spectrum, Cartesian components, or per-atom
        scalar spectra.
    atom_indices
        Canonical atom indices to plot for ``projection='per_atom'``. When
        omitted, all stored per-atom curves are plotted only if there are at
        most twelve. Larger stored sets require an explicit subset.
    normalize_for_display
        Divide all selected curves by one common maximum absolute amplitude.
        This explicit display operation preserves relative amplitudes among
        the selected curves, changes only plotted copies, and does not alter
        the result or its scientific normalization.
    ax
        Existing Matplotlib axes. A new figure and axes are created when
        omitted.

    Returns
    -------
    tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]
        The figure and axes containing the plot.

    Notes
    -----
    The function does not call :func:`matplotlib.pyplot.show`, save files,
    recompute spectra, infer phonon modes, or relabel a generic VDOS as a
    phonon density of states.
    """
    if not isinstance(result, (VelocitySpectrumResult, VDOSResult)):
        raise TypeError("result must be a VelocitySpectrumResult or VDOSResult.")
    if not isinstance(normalize_for_display, bool):
        raise TypeError("normalize_for_display must be a boolean.")
    if ax is not None and not isinstance(ax, Axes):
        raise TypeError("ax must be a matplotlib.axes.Axes instance or None.")

    x_values, x_label = _axis_values_and_label(result, x_axis)
    curves, labels = _plot_curves(
        result,
        projection=projection,
        atom_indices=atom_indices,
    )

    plotted = np.array(curves, dtype=np.float64, copy=True)
    if normalize_for_display:
        scale = float(np.max(np.abs(plotted)))
        if not np.isfinite(scale) or scale <= 0.0:
            raise ValueError(
                "Display normalization requires at least one nonzero finite value."
            )
        plotted /= scale

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    for column, curve_label in enumerate(labels):
        ax.plot(x_values, plotted[:, column], label=curve_label)

    ax.set_xlabel(x_label)
    ax.set_ylabel(
        _ordinate_label(result, normalize_for_display=normalize_for_display)
    )
    ax.grid(True, which="major", alpha=0.25)
    if projection != "total":
        ax.legend()

    return fig, ax
