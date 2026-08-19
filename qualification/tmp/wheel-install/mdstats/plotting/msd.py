"""Plotting helpers for mean-square displacement results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np

from ..analysis.msd import MSDResult

TimeUnit = Literal["fs", "ps", "ns"]
MSDInput = MSDResult | Sequence[MSDResult] | Mapping[str, MSDResult]

_TIME_FACTORS: dict[str, float] = {
    "fs": 1.0e3,  # internal time is ps
    "ps": 1.0,
    "ns": 1.0e-3,
}


def _normalise_results(
    results: MSDInput,
    *,
    labels: Sequence[str] | None,
    label: str | None,
) -> list[tuple[str, MSDResult]]:
    """Return a validated list of ``(label, result)`` pairs."""
    if isinstance(results, MSDResult):
        if labels is not None:
            raise ValueError("labels is only valid when plotting multiple MSD results.")
        default = (
            "Fixed-origin MSD"
            if results.mode == "fixed_origin"
            else "Time-averaged MSD"
        )
        return [(label or default, results)]

    if label is not None:
        raise ValueError("label is only valid when plotting a single MSD result.")

    if isinstance(results, Mapping):
        if labels is not None:
            raise ValueError(
                "Do not pass labels when results is a mapping; mapping keys are labels."
            )
        pairs = list(results.items())
    else:
        values = list(results)
        if not values:
            raise ValueError("At least one MSD result is required.")
        if labels is None:
            pairs = [(f"MSD {index + 1}", value) for index, value in enumerate(values)]
        else:
            if len(labels) != len(values):
                raise ValueError("labels must have the same length as results.")
            pairs = list(zip(labels, values, strict=True))

    if not pairs:
        raise ValueError("At least one MSD result is required.")
    for curve_label, result in pairs:
        if not isinstance(curve_label, str) or not curve_label:
            raise ValueError("Every MSD curve label must be a non-empty string.")
        if not isinstance(result, MSDResult):
            raise TypeError("Every plotted object must be an MSDResult.")
    return pairs


def plot_msd(
    result: MSDInput,
    *,
    ax: Axes | None = None,
    show_components: bool = False,
    show_per_atom: bool = False,
    per_atom_indices: Sequence[int] | None = None,
    atom_labels: Mapping[int, str] | None = None,
    time_unit: TimeUnit = "ps",
    label: str | None = None,
    labels: Sequence[str] | None = None,
    title: str | None = None,
    log_x: bool = False,
    log_y: bool = False,
    grid: bool = True,
) -> tuple[Figure, Axes]:
    """Plot one or more :class:`~mdstats.analysis.msd.MSDResult` objects.

    Parameters
    ----------
    result
        One MSD result, a sequence of results, or a mapping from legend labels
        to results. A mapping is the most convenient form for comparing
        multiple species, for example ``{"Na": na_msd, "K": k_msd}``.
    ax
        Existing Matplotlib axes. A new figure and axes are created when
        omitted.
    show_components
        Plot ``MSD_x``, ``MSD_y``, and ``MSD_z`` in addition to each scalar
        MSD. With multiple results, component labels are prefixed by the
        corresponding result label.
    show_per_atom
        Plot per-atom MSD curves. Each result must have been computed with
        ``per_atom=True``.
    per_atom_indices
        Canonical trajectory atom indices to plot. When omitted, all selected
        atoms in each result are plotted.
    atom_labels
        Optional mapping from canonical atom index to a custom legend label,
        for example ``{12: "Na atom 12", 18: "K atom 18"}``.
    time_unit
        Unit used for the horizontal axis: ``"fs"``, ``"ps"``, or ``"ns"``.
    label
        Legend label for a single result. Invalid for multiple results.
    labels
        Legend labels for a sequence of results. When ``result`` is a mapping,
        its keys are used directly and this argument must be omitted.
    title
        Optional axes title.
    log_x, log_y
        Use logarithmic scaling on the selected axes.
    grid
        Draw a light major grid.

    Returns
    -------
    tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]
        The figure and axes containing the plot.

    Notes
    -----
    Matplotlib assigns a different default color to each plotted line. The
    function does not call :func:`matplotlib.pyplot.show`; callers retain full
    control over display, layout, and file output.
    """
    if time_unit not in _TIME_FACTORS:
        raise ValueError("time_unit must be one of 'fs', 'ps', or 'ns'.")

    curves = _normalise_results(result, labels=labels, label=label)

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    multiple_results = len(curves) > 1

    for curve_label, current in curves:
        times = (
            np.asarray(current.lag_times, dtype=np.float64) * _TIME_FACTORS[time_unit]
        )
        ax.plot(times, current.msd, label=curve_label)

        if show_components:
            for axis_name, component in zip(
                "xyz", np.asarray(current.components).T, strict=True
            ):
                component_label = rf"MSD$_{axis_name}$"
                if multiple_results:
                    component_label = f"{curve_label} {component_label}"
                ax.plot(times, component, label=component_label)

        if show_per_atom:
            if current.per_atom_msd is None:
                raise ValueError(
                    f"Per-atom MSD data are unavailable for '{curve_label}'. "
                    "Recompute with per_atom=True."
                )

            selected_ids = np.asarray(current.atom_indices, dtype=np.int64)
            if per_atom_indices is None:
                columns = np.arange(current.n_atoms, dtype=np.int64)
            else:
                requested = np.asarray(per_atom_indices, dtype=np.int64)
                if requested.ndim != 1:
                    raise ValueError("per_atom_indices must be one-dimensional.")
                lookup = {
                    int(atom_id): column for column, atom_id in enumerate(selected_ids)
                }
                columns = np.asarray(
                    [
                        lookup[int(atom_id)]
                        for atom_id in requested
                        if int(atom_id) in lookup
                    ],
                    dtype=np.int64,
                )

            for column in columns:
                atom_id = int(selected_ids[column])
                atom_label = (
                    atom_labels.get(atom_id, f"Atom {atom_id}")
                    if atom_labels is not None
                    else f"Atom {atom_id}"
                )
                if multiple_results:
                    atom_label = f"{curve_label}: {atom_label}"
                ax.plot(
                    times,
                    current.per_atom_msd[:, column],
                    label=atom_label,
                    alpha=0.7,
                )

    if show_per_atom and per_atom_indices is not None:
        available = {
            int(atom_id)
            for _, current in curves
            for atom_id in np.asarray(current.atom_indices, dtype=np.int64)
        }
        missing = [
            int(index) for index in per_atom_indices if int(index) not in available
        ]
        if missing:
            raise ValueError(
                f"Requested atom indices are absent from all MSD selections: {missing}."
            )

    ax.set_xlabel(f"Time lag ({time_unit})")
    ax.set_ylabel(r"MSD ($\mathrm{\AA}^2$)")
    if title is not None:
        ax.set_title(title)
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    if grid:
        ax.grid(True, which="major", alpha=0.25)
    if len(ax.lines) > 1 or any(line.get_label() for line in ax.lines):
        ax.legend()

    return fig, ax
