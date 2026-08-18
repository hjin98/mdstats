"""Plotting helpers for integer coordination-state distributions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np

from ..analysis.coordination import CoordinationResult

CoordinationInput = (
    CoordinationResult | Sequence[CoordinationResult] | Mapping[str, CoordinationResult]
)
ProbabilityUnit = Literal["fraction", "percent"]


def _normalise_coordination_results(
    results: CoordinationInput,
    *,
    labels: Sequence[str] | None,
    label: str | None,
) -> list[tuple[str, CoordinationResult]]:
    """Return validated ``(label, result)`` pairs."""
    if isinstance(results, CoordinationResult):
        if labels is not None:
            raise ValueError("labels is only valid for multiple results.")
        default = f"{results.species_a}-{results.species_b}"
        return [(label or default, results)]

    if label is not None:
        raise ValueError("label is only valid for a single result.")
    if isinstance(results, Mapping):
        if labels is not None:
            raise ValueError(
                "Do not pass labels when results is a mapping; mapping keys are labels."
            )
        pairs = list(results.items())
    else:
        values = list(results)
        if not values:
            raise ValueError("At least one CoordinationResult is required.")
        if labels is None:
            pairs = [
                (f"{value.species_a}-{value.species_b}", value) for value in values
            ]
        else:
            if len(labels) != len(values):
                raise ValueError("labels must have the same length as results.")
            pairs = list(zip(labels, values, strict=True))

    if not pairs:
        raise ValueError("At least one CoordinationResult is required.")
    for panel_label, result in pairs:
        if not isinstance(panel_label, str) or not panel_label:
            raise ValueError("Every panel label must be a non-empty string.")
        if not isinstance(result, CoordinationResult):
            raise TypeError("Every plotted object must be a CoordinationResult.")
    return pairs


def _atlas_shape(n_results: int, ncols: int | None) -> tuple[int, int]:
    """Return a compact atlas shape for ``n_results`` panels."""
    if ncols is None:
        ncols_resolved = max(1, math.ceil(math.sqrt(n_results)))
    else:
        if isinstance(ncols, bool) or not isinstance(ncols, int) or ncols <= 0:
            raise ValueError("ncols must be a positive integer or None.")
        ncols_resolved = min(ncols, n_results)
    nrows = math.ceil(n_results / ncols_resolved)
    return nrows, ncols_resolved


def plot_coordination_distribution(
    result: CoordinationInput,
    *,
    axes: Axes | Sequence[Axes] | np.ndarray | None = None,
    label: str | None = None,
    labels: Sequence[str] | None = None,
    probability_unit: ProbabilityUnit = "fraction",
    annotate: bool = True,
    sharex: bool = False,
    sharey: bool = False,
    title: str | None = None,
    grid: bool = True,
    ncols: int | None = None,
    panel_size: tuple[float, float] = (4.8, 3.4),
    trim_zero_probability: bool = True,
    x_margin: float = 0.55,
    annotation_text_alpha: float = 0.65,
    annotation_box_alpha: float = 0.22,
) -> tuple[Figure, np.ndarray]:
    """Plot one or more coordination distributions as a subplot atlas.

    Parameters
    ----------
    result
        One :class:`~mdstats.analysis.coordination.CoordinationResult`, a
        sequence of results, or a mapping from panel labels to results.
    axes
        Existing axes. A single :class:`matplotlib.axes.Axes` is valid only for
        one result. An axes sequence or array may contain extra panels; unused
        panels are hidden. When omitted, a compact atlas is created.
    label, labels
        Panel labels for one result or a result sequence. Mapping keys are used
        directly when ``result`` is a mapping.
    probability_unit
        Display probabilities as fractions or percentages.
    annotate
        Show mean, standard deviation, and coordination cutoff in each panel.
    sharex, sharey
        Share axes for an automatically created atlas.
    title
        Optional figure-level title.
    grid
        Draw a light horizontal major grid in each active panel.
    ncols
        Number of atlas columns when ``axes`` is omitted. The default chooses
        a compact near-square layout. For example, two results use a 1x2 atlas
        and four results use a 2x2 atlas.
    panel_size
        Approximate ``(width, height)`` in inches for each atlas panel.
    trim_zero_probability
        Restrict each panel to the smallest integer coordination range that
        contains all states with nonzero probability. Disable this when a
        common fixed x-range is more useful for visual comparison.
    x_margin
        Extra horizontal margin, in coordination-number units, added outside
        the first and last displayed integer states.
    annotation_text_alpha
        Opacity of the summary annotation text.
    annotation_box_alpha
        Opacity of the summary annotation background box.

    Returns
    -------
    tuple[matplotlib.figure.Figure, numpy.ndarray]
        The figure and a two-dimensional axes array. Unused axes, if any, are
        hidden but retained in the returned atlas.

    Notes
    -----
    The function consumes precomputed ``CoordinationResult`` objects and never
    recomputes coordination numbers. Each species pair is plotted in a
    separate panel because discrete bar distributions are clearer as an atlas
    than as overlapping bars on one axes.
    """
    if probability_unit not in {"fraction", "percent"}:
        raise ValueError("probability_unit must be 'fraction' or 'percent'.")
    if (
        not isinstance(panel_size, tuple)
        or len(panel_size) != 2
        or any(not np.isfinite(value) or value <= 0.0 for value in panel_size)
    ):
        raise ValueError("panel_size must be a tuple of two positive finite values.")
    if not isinstance(trim_zero_probability, bool):
        raise TypeError("trim_zero_probability must be a boolean.")
    if not np.isfinite(x_margin) or x_margin < 0.0:
        raise ValueError("x_margin must be a non-negative finite value.")
    for name, value in (
        ("annotation_text_alpha", annotation_text_alpha),
        ("annotation_box_alpha", annotation_box_alpha),
    ):
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must lie in [0, 1].")

    pairs = _normalise_coordination_results(result, labels=labels, label=label)
    n_results = len(pairs)

    if axes is None:
        nrows, ncols_resolved = _atlas_shape(n_results, ncols)
        fig, ax_array = plt.subplots(
            nrows,
            ncols_resolved,
            squeeze=False,
            sharex=sharex,
            sharey=sharey,
            figsize=(panel_size[0] * ncols_resolved, panel_size[1] * nrows),
        )
    elif isinstance(axes, Axes):
        if n_results != 1:
            raise ValueError(
                "A single Axes can only be used for one coordination result."
            )
        if ncols is not None:
            raise ValueError("ncols is only valid when axes is omitted.")
        fig = axes.figure
        ax_array = np.asarray([[axes]], dtype=object)
    else:
        if ncols is not None:
            raise ValueError("ncols is only valid when axes is omitted.")
        original = np.asarray(axes, dtype=object)
        if original.ndim == 0:
            raise TypeError("axes must be an Axes or an array-like of Axes.")
        ax_array = original.reshape(1, -1) if original.ndim == 1 else original
        flat_axes = ax_array.ravel()
        if flat_axes.size < n_results:
            raise ValueError(
                f"axes must contain at least {n_results} Axes objects; "
                f"received {flat_axes.size}."
            )
        for ax in flat_axes:
            if not isinstance(ax, Axes):
                raise TypeError("Every item in axes must be a matplotlib Axes.")
        figures = {id(ax.figure): ax.figure for ax in flat_axes}
        if len(figures) != 1:
            raise ValueError("All supplied axes must belong to the same figure.")
        fig = flat_axes[0].figure

    flat_axes = ax_array.ravel()
    active_axes = flat_axes[:n_results]
    unused_axes = flat_axes[n_results:]

    scale = 100.0 if probability_unit == "percent" else 1.0
    ylabel = "Probability (%)" if probability_unit == "percent" else "Probability"
    global_max = max(
        float(np.max(current.probabilities) * scale) for _, current in pairs
    )

    for ax, (panel_label, current) in zip(active_axes, pairs, strict=True):
        heights = current.probabilities * scale
        ax.bar(current.coordination_values, heights, width=0.8)

        positive = np.flatnonzero(current.probabilities > 0.0)
        if positive.size == 0:
            raise ValueError(
                f"Coordination distribution '{panel_label}' has no nonzero probability."
            )
        first_positive = int(positive[0])
        last_positive = int(positive[-1])
        visible_values = current.coordination_values[first_positive : last_positive + 1]
        if trim_zero_probability:
            xmin = float(visible_values[0]) - x_margin
            xmax = float(visible_values[-1]) + x_margin
            ax.set_xlim(xmin, xmax)
            ax.set_xticks(visible_values)
        else:
            ax.set_xticks(current.coordination_values)

        ax.set_xlabel("Coordination number")
        ax.set_ylabel(ylabel)
        ax.set_title(panel_label, pad=8.0)

        panel_max = global_max if sharey else float(np.max(heights))
        minimum_headroom = 1.0 if probability_unit == "percent" else 0.01
        ax.set_ylim(0.0, max(minimum_headroom, 1.18 * panel_max))

        if annotate:
            source = (
                "manual"
                if current.pair_cutoff.source == "manual"
                else "RDF first minimum"
            )
            annotation = (
                f"mean = {current.mean:.3g}\n"
                f"std = {current.std:.3g}\n"
                f"cutoff = {current.pair_cutoff.radius:.3g} Å ({source})"
            )

            midpoint = 0.5 * (visible_values[0] + visible_values[-1])
            left_mass = float(np.sum(heights[current.coordination_values <= midpoint]))
            right_mass = float(np.sum(heights[current.coordination_values > midpoint]))
            if left_mass <= right_mass:
                annotation_x = 0.02
                horizontal_alignment = "left"
            else:
                annotation_x = 0.98
                horizontal_alignment = "right"

            ax.text(
                annotation_x,
                0.96,
                annotation,
                transform=ax.transAxes,
                ha=horizontal_alignment,
                va="top",
                alpha=annotation_text_alpha,
                bbox={
                    "boxstyle": "round,pad=0.28",
                    "facecolor": "white",
                    "edgecolor": "0.35",
                    "linewidth": 0.7,
                    "alpha": annotation_box_alpha,
                },
            )
        if grid:
            ax.grid(True, axis="y", which="major", alpha=0.25)
        ax.set_axisbelow(True)

    for ax in unused_axes:
        ax.set_visible(False)

    if title is not None:
        fig.suptitle(title)
    if axes is None:
        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95 if title is not None else 1.0))
    return fig, ax_array
