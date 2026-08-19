"""Plotting helpers for running VACF-derived diffusion curves.

Rendering is delegated to Matplotlib [Hunter, Comput. Sci. Eng. 9, 90-95
(2007), DOI: 10.1109/MCSE.2007.55].  The unit conversion, explicit distinction
between a running Green-Kubo integral and an accepted asymptotic coefficient,
and the multi-result labeling contract are mdstats design decisions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np

from ..analysis.vacf_transport import VACFDiffusionResult

TimeUnit = Literal["fs", "ps", "ns"]
DiffusionUnit = Literal["angstrom2/ps", "cm2/s"]
DiffusionInput = (
    VACFDiffusionResult
    | Sequence[VACFDiffusionResult]
    | Mapping[str, VACFDiffusionResult]
)

_TIME_FACTORS: dict[str, float] = {
    "fs": 1.0e3,  # stored time is ps
    "ps": 1.0,
    "ns": 1.0e-3,
}


def _default_label(result: VACFDiffusionResult) -> str:
    if result.component == "scalar":
        return r"$D(t)$"
    return rf"$D_{result.component}(t)$"


def _normalise_results(
    results: DiffusionInput,
    *,
    labels: Sequence[str] | None,
    label: str | None,
) -> list[tuple[str, VACFDiffusionResult]]:
    """Return a validated list of labelled running-diffusion results."""
    if isinstance(results, VACFDiffusionResult):
        if labels is not None:
            raise ValueError(
                "labels is only valid when plotting multiple diffusion results."
            )
        return [(label or _default_label(results), results)]

    if label is not None:
        raise ValueError("label is only valid when plotting a single result.")

    if isinstance(results, Mapping):
        if labels is not None:
            raise ValueError(
                "Do not pass labels when result is a mapping; mapping keys are labels."
            )
        pairs = list(results.items())
    else:
        values = list(results)
        if not values:
            raise ValueError("At least one VACF diffusion result is required.")
        if labels is None:
            pairs = [(_default_label(value), value) for value in values]
        else:
            if len(labels) != len(values):
                raise ValueError("labels must have the same length as result.")
            pairs = list(zip(labels, values, strict=True))

    if not pairs:
        raise ValueError("At least one VACF diffusion result is required.")
    for curve_label, current in pairs:
        if not isinstance(curve_label, str) or not curve_label:
            raise ValueError("Every diffusion-curve label must be a non-empty string.")
        if not isinstance(current, VACFDiffusionResult):
            raise TypeError("Every plotted object must be a VACFDiffusionResult.")
    return pairs


def _diffusion_values(
    result: VACFDiffusionResult,
    unit: DiffusionUnit,
) -> tuple[np.ndarray, str]:
    if unit == "angstrom2/ps":
        return (
            np.asarray(result.running_diffusion_a2_per_ps, dtype=np.float64),
            r"Running self-diffusion $D(t)$ ($\mathrm{\AA}^2/\mathrm{ps}$)",
        )
    if unit == "cm2/s":
        return (
            np.asarray(result.running_diffusion_cm2_per_s, dtype=np.float64),
            r"Running self-diffusion $D(t)$ ($\mathrm{cm}^2/\mathrm{s}$)",
        )
    raise ValueError("diffusion_unit must be 'angstrom2/ps' or 'cm2/s'.")


def plot_vacf_diffusion(
    result: DiffusionInput,
    *,
    ax: Axes | None = None,
    time_unit: TimeUnit = "ps",
    diffusion_unit: DiffusionUnit = "cm2/s",
    label: str | None = None,
    labels: Sequence[str] | None = None,
    title: str | None = None,
    show_zero_line: bool = True,
    grid: bool = True,
) -> tuple[Figure, Axes]:
    """Plot one or more running Green-Kubo self-diffusion curves.

    Parameters
    ----------
    result
        One :class:`~mdstats.analysis.vacf_transport.VACFDiffusionResult`, a
        sequence of results, or a mapping from legend labels to results.
    ax
        Existing Matplotlib axes. A new figure and axes are created when
        omitted.
    time_unit
        Horizontal-axis unit: ``"fs"``, ``"ps"``, or ``"ns"``.
    diffusion_unit
        Vertical-axis unit: internal ``"angstrom2/ps"`` or ``"cm2/s"``.
    label
        Legend label for a single result. Invalid for multiple results.
    labels
        Labels for a sequence of results. Mapping keys are used directly.
    title
        Optional axes title.
    show_zero_line
        Draw a light horizontal reference at zero.
    grid
        Draw a light major grid.

    Returns
    -------
    tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]
        The figure and axes containing the plot.

    Notes
    -----
    The plotted curve is the finite-time running Green-Kubo integral.  The
    function does not identify a plateau, fit a correlation tail, or label the
    final sample as a converged diffusion coefficient.
    """
    if time_unit not in _TIME_FACTORS:
        raise ValueError("time_unit must be 'fs', 'ps', or 'ns'.")
    if not isinstance(show_zero_line, bool):
        raise TypeError("show_zero_line must be a boolean.")
    if not isinstance(grid, bool):
        raise TypeError("grid must be a boolean.")
    if ax is not None and not isinstance(ax, Axes):
        raise TypeError("ax must be a matplotlib.axes.Axes instance or None.")

    curves = _normalise_results(result, labels=labels, label=label)

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    y_label: str | None = None
    for curve_label, current in curves:
        times = np.asarray(current.lag_times, dtype=np.float64) * _TIME_FACTORS[
            time_unit
        ]
        values, current_y_label = _diffusion_values(current, diffusion_unit)
        if y_label is None:
            y_label = current_y_label
        ax.plot(times, values, label=curve_label)

    if show_zero_line:
        ax.axhline(0.0, linewidth=0.8, alpha=0.45)
    ax.set_xlabel(f"Time lag ({time_unit})")
    ax.set_ylabel(y_label or "Running self-diffusion D(t)")
    if title is not None:
        ax.set_title(title)
    if grid:
        ax.grid(True, which="major", alpha=0.25)

    if len(curves) > 1 or label is not None or isinstance(result, Mapping):
        ax.legend()

    return fig, ax
