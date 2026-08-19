"""Plotting helpers for pair radial-distribution results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ..analysis.rdf import RDFFeature, RDFResult

RDFInput = RDFResult | Sequence[RDFResult] | Mapping[str, RDFResult]


@dataclass(slots=True)
class _PendingFeatureAnnotation:
    """Feature marker whose text is laid out after all curves are drawn."""

    feature: RDFFeature
    color: Any
    feature_name: str
    curve_label: str


def _normalise_rdf_results(
    results: RDFInput,
    *,
    labels: Sequence[str] | None,
    label: str | None,
) -> list[tuple[str, RDFResult]]:
    """Return a validated list of ``(label, rdf)`` pairs."""
    if isinstance(results, RDFResult):
        if labels is not None:
            raise ValueError("labels is only valid when plotting multiple RDF results.")
        default = f"{results.species_a}-{results.species_b}"
        return [(label or default, results)]

    if label is not None:
        raise ValueError("label is only valid when plotting a single RDF result.")

    if isinstance(results, Mapping):
        if labels is not None:
            raise ValueError(
                "Do not pass labels when results is a mapping; mapping keys are labels."
            )
        pairs = list(results.items())
    else:
        values = list(results)
        if not values:
            raise ValueError("At least one RDF result is required.")
        if labels is None:
            pairs = [
                (f"{value.species_a}-{value.species_b}", value) for value in values
            ]
        else:
            if len(labels) != len(values):
                raise ValueError("labels must have the same length as results.")
            pairs = list(zip(labels, values, strict=True))

    if not pairs:
        raise ValueError("At least one RDF result is required.")
    for curve_label, result in pairs:
        if not isinstance(curve_label, str) or not curve_label:
            raise ValueError("Every RDF curve label must be a non-empty string.")
        if not isinstance(result, RDFResult):
            raise TypeError("Every plotted object must be an RDFResult.")
    return pairs


def _feature_label_text(annotation: _PendingFeatureAnnotation) -> str:
    """Return a compact, human-readable feature label."""
    return (
        f"{annotation.curve_label} — {annotation.feature_name}: "
        f"{annotation.feature.radius:.2f} $\\mathrm{{\\AA}}$"
    )


def _feature_row_spacing(ax: Axes, n_rows: int) -> float:
    """Return a safe axes-fraction spacing for stacked feature labels.

    The spacing is based on the rendered axes height so labels remain separated
    on both compact and presentation-sized figures.  A conservative fallback
    is used when the renderer has not yet established a useful axes extent.
    """
    if n_rows <= 1:
        return 0.0

    figure = ax.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    axes_height = float(ax.get_window_extent(renderer).height)
    if axes_height <= 0.0:
        return 0.075

    font_size_points = float(plt.rcParams["font.size"]) * 0.85
    line_height_pixels = 1.65 * font_size_points * figure.dpi / 72.0
    return max(0.075, min(0.11, line_height_pixels / axes_height))


def _annotate_rdf_features(
    ax: Axes,
    annotations: Sequence[_PendingFeatureAnnotation],
    *,
    text_alpha: float,
    box_alpha: float,
    arrow_alpha: float,
) -> None:
    """Lay out RDF feature labels inside the axes without collisions.

    All feature labels occupy a compact rail descending from the upper-right
    corner.  Peak labels are placed first, followed by minimum labels. Text is
    positioned in axes coordinates while arrows terminate at the feature in
    data coordinates. This keeps labels inside the plot box, away from the
    title and from the upper-left legend, and prevents labels from overlapping
    one another.
    """
    peaks = [item for item in annotations if item.feature_name == "First peak"]
    minima = [item for item in annotations if item.feature_name == "First minimum"]

    ordered = [*peaks, *minima]
    row_spacing = _feature_row_spacing(ax, len(ordered))

    def add_annotation(
        item: _PendingFeatureAnnotation,
        *,
        x_fraction: float,
        y_fraction: float,
        vertical_alignment: str,
    ) -> None:
        ax.annotate(
            _feature_label_text(item),
            xy=(item.feature.radius, item.feature.value),
            xycoords="data",
            xytext=(x_fraction, y_fraction),
            textcoords="axes fraction",
            ha="right",
            va=vertical_alignment,
            color=item.color,
            fontsize="small",
            alpha=text_alpha,
            clip_on=True,
            annotation_clip=True,
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": box_alpha,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": item.color,
                "alpha": arrow_alpha,
                "linewidth": 0.8,
                "shrinkA": 2.0,
                "shrinkB": 2.0,
            },
            zorder=6,
        )

    for row, item in enumerate(ordered):
        add_annotation(
            item,
            x_fraction=0.98,
            y_fraction=0.98 - row * row_spacing,
            vertical_alignment="top",
        )


def plot_pair_rdf(
    result: RDFInput,
    *,
    ax: Axes | None = None,
    label: str | None = None,
    labels: Sequence[str] | None = None,
    title: str | None = None,
    smoothing_sigma: float | None = None,
    show_raw: bool = True,
    show_first_peak: bool = False,
    show_first_minimum: bool = False,
    first_peak_options: Mapping[str, Any] | None = None,
    first_minimum_options: Mapping[str, Any] | None = None,
    feature_annotation_text_alpha: float = 0.62,
    feature_annotation_box_alpha: float = 0.18,
    feature_annotation_arrow_alpha: float = 0.45,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    grid: bool = True,
) -> tuple[Figure, Axes]:
    """Plot one or more pair RDF curves on a single set of axes.

    Parameters
    ----------
    result
        One :class:`~mdstats.analysis.rdf.RDFResult`, a sequence of results, or
        a mapping from legend labels to results.
    ax
        Existing matplotlib axes. A new figure and axes are created when
        omitted.
    label, labels
        Legend labels for one result or a sequence of results.
    title
        Optional axes title.
    smoothing_sigma
        Gaussian smoothing width in angstrom. When provided, the smoothed RDF
        is plotted. If ``show_raw`` is also ``True``, the unsmoothed RDF is
        drawn underneath with lower opacity.
    show_raw
        Plot the raw histogram RDF. When ``smoothing_sigma`` is ``None``, this
        has no effect because the raw curve is the only curve available.
    show_first_peak
        Mark the detected first structural peak and annotate its radius.
    show_first_minimum
        Mark the detected first-shell minimum and annotate its radius.
    first_peak_options
        Optional keyword arguments forwarded to
        :meth:`mdstats.analysis.rdf.RDFResult.first_peak`.
    first_minimum_options
        Optional keyword arguments forwarded to
        :meth:`mdstats.analysis.rdf.RDFResult.first_minimum`.
    feature_annotation_text_alpha
        Opacity of peak and minimum label text.
    feature_annotation_box_alpha
        Opacity of the label background boxes.
    feature_annotation_arrow_alpha
        Opacity of the arrows connecting labels to detected features.
    xlim, ylim
        Optional axis limits.
    grid
        Draw a light major grid.

    Notes
    -----
    Feature labels are arranged in a compact rail inside the upper-right of
    the plotting box: peaks first, then minima. This avoids label collisions
    and keeps annotations away from the upper-left legend and the axes title.
    """
    for name, value in (
        ("feature_annotation_text_alpha", feature_annotation_text_alpha),
        ("feature_annotation_box_alpha", feature_annotation_box_alpha),
        ("feature_annotation_arrow_alpha", feature_annotation_arrow_alpha),
    ):
        if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{name} must lie in [0, 1].")

    curves = _normalise_rdf_results(result, labels=labels, label=label)
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    peak_options = dict(first_peak_options or {})
    minimum_options = dict(first_minimum_options or {})
    annotations: list[_PendingFeatureAnnotation] = []

    for curve_label, rdf in curves:
        if smoothing_sigma is None:
            line = ax.plot(rdf.r, rdf.g_r, label=curve_label)[0]
        else:
            base_color = None
            if show_raw:
                raw_label = f"{curve_label} (raw)" if len(curves) > 1 else "Raw"
                base_color = ax.plot(
                    rdf.r,
                    rdf.g_r,
                    label=raw_label,
                    alpha=0.35,
                )[0].get_color()
            smooth = rdf.smoothed(sigma=smoothing_sigma)
            line = ax.plot(
                rdf.r,
                smooth,
                label=curve_label,
                color=base_color,
            )[0]

        if show_first_peak:
            feature = rdf.first_peak(**peak_options)
            ax.axvline(
                feature.radius,
                color=line.get_color(),
                linestyle=":",
                alpha=0.65,
                label="_nolegend_",
            )
            ax.plot(
                feature.radius,
                feature.value,
                marker="o",
                linestyle="None",
                color=line.get_color(),
                label="_nolegend_",
                zorder=5,
            )
            annotations.append(
                _PendingFeatureAnnotation(
                    feature=feature,
                    color=line.get_color(),
                    feature_name="First peak",
                    curve_label=curve_label,
                )
            )

        if show_first_minimum:
            feature = rdf.first_minimum(**minimum_options)
            ax.axvline(
                feature.radius,
                color=line.get_color(),
                linestyle="--",
                alpha=0.7,
                label="_nolegend_",
            )
            ax.plot(
                feature.radius,
                feature.value,
                marker="o",
                linestyle="None",
                color=line.get_color(),
                label="_nolegend_",
                zorder=5,
            )
            annotations.append(
                _PendingFeatureAnnotation(
                    feature=feature,
                    color=line.get_color(),
                    feature_name="First minimum",
                    curve_label=curve_label,
                )
            )

    ax.set_xlabel(r"Distance $r$ ($\mathrm{\AA}$)")
    ax.set_ylabel(r"$g(r)$")
    if title is not None:
        ax.set_title(title)
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)
    if grid:
        ax.grid(True, which="major", alpha=0.25)
    if (
        len(curves) > 1
        or smoothing_sigma is not None
        or show_first_peak
        or show_first_minimum
    ):
        legend_location = "upper left" if annotations else "best"
        ax.legend(loc=legend_location)

    if annotations:
        _annotate_rdf_features(
            ax,
            annotations,
            text_alpha=float(feature_annotation_text_alpha),
            box_alpha=float(feature_annotation_box_alpha),
            arrow_alpha=float(feature_annotation_arrow_alpha),
        )

    return fig, ax
