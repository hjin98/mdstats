"""Plot completed topology-statistics results without recomputing analysis.

The TS5 plotting layer consumes immutable TS0--TS4 statistics objects.  It does
not inspect source catalogs, construct graph descriptors, or infer temporal
meaning for ensembles.
"""

from __future__ import annotations

from typing import Literal

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np
from ase.data import chemical_symbols

from ..analysis.topology_statistics import (
    AtomicConnectivityStatistics,
    FrameworkTopologyStatistics,
    StateTransitionStatistics,
    TopologyStatistics,
)

ProbabilityUnit = Literal["fraction", "percent"]
TopologyBranch = Literal["atomic", "framework"]


def _atomic_branch(
    result: AtomicConnectivityStatistics | TopologyStatistics,
) -> AtomicConnectivityStatistics:
    if isinstance(result, TopologyStatistics):
        return result.atomic
    if not isinstance(result, AtomicConnectivityStatistics):
        raise TypeError("Expected AtomicConnectivityStatistics or TopologyStatistics.")
    return result


def _framework_branch(
    result: FrameworkTopologyStatistics | TopologyStatistics,
) -> FrameworkTopologyStatistics:
    if isinstance(result, TopologyStatistics):
        return result.framework
    if not isinstance(result, FrameworkTopologyStatistics):
        raise TypeError("Expected FrameworkTopologyStatistics or TopologyStatistics.")
    return result


def _branch(
    result: AtomicConnectivityStatistics
    | FrameworkTopologyStatistics
    | TopologyStatistics,
    branch: TopologyBranch,
) -> AtomicConnectivityStatistics | FrameworkTopologyStatistics:
    return _atomic_branch(result) if branch == "atomic" else _framework_branch(result)


def _requested_pair_label(left: int | str, right: int | str) -> str:
    def symbol(value: int | str) -> str:
        if isinstance(value, str):
            return value.strip()
        return chemical_symbols[int(value)]

    return f"{symbol(left)}-{symbol(right)}"


def _new_axes(
    ax: Axes | None, *, figsize: tuple[float, float] = (7.2, 4.2)
) -> tuple[Figure, Axes]:
    if ax is None:
        return plt.subplots(figsize=figsize)
    if not isinstance(ax, Axes):
        raise TypeError("ax must be a matplotlib Axes or None.")
    return ax.figure, ax


def _probability_scale(unit: ProbabilityUnit) -> tuple[float, str]:
    if unit == "fraction":
        return 1.0, "Probability"
    if unit == "percent":
        return 100.0, "Probability (%)"
    raise ValueError("probability_unit must be 'fraction' or 'percent'.")


def _finish(
    fig: Figure, ax: Axes, *, grid_axis: str | None = None
) -> tuple[Figure, Axes]:
    if grid_axis is not None:
        ax.grid(True, axis=grid_axis, alpha=0.25)
    fig.tight_layout()
    return fig, ax


def plot_pair_count_distribution(
    result: AtomicConnectivityStatistics | TopologyStatistics,
    left: int | str,
    right: int | str,
    *,
    ax: Axes | None = None,
    probability_unit: ProbabilityUnit = "fraction",
    title: str | None = None,
    annotate_summary: bool = True,
) -> tuple[Figure, Axes]:
    """Plot the exact integer PMF of one atomic species-pair contact count."""
    stats = _atomic_branch(result).pair(left, right)
    display_label = _requested_pair_label(left, right)
    scale, ylabel = _probability_scale(probability_unit)
    fig, ax = _new_axes(ax)
    distribution = stats.contact_count_distribution
    values = distribution.probabilities * scale
    ax.bar(distribution.support, values)
    ax.set_xlabel(f"{display_label} contact count")
    ax.set_ylabel(ylabel)
    ax.set_title(title or f"{display_label} contact-count distribution")
    ax.set_xticks(distribution.support)
    if annotate_summary:
        summary = distribution.summary
        text = (
            f"mean={summary.mean:.3f}\n"
            f"SD={summary.population_standard_deviation:.3f}\n"
            f"range={int(summary.minimum)}-{int(summary.maximum)}"
        )
        ax.text(
            0.98,
            0.96,
            text,
            transform=ax.transAxes,
            ha="right",
            va="top",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.7},
        )
    return _finish(fig, ax, grid_axis="y")


def plot_pair_count_timeseries(
    result: AtomicConnectivityStatistics | TopologyStatistics,
    left: int | str,
    right: int | str,
    *,
    ax: Axes | None = None,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot a species-pair contact count over time, frame, or sample index."""
    atomic = _atomic_branch(result)
    stats = atomic.pair(left, right)
    display_label = _requested_pair_label(left, right)
    fig, ax = _new_axes(ax)
    ax.plot(atomic.axis.x_values, stats.contact_count_series.values)
    ax.set_xlabel(atomic.axis.x_label)
    ax.set_ylabel(f"{display_label} contact count")
    qualifier = (
        "time series"
        if atomic.axis.frame_semantics.value == "trajectory"
        else "sample series"
    )
    ax.set_title(title or f"{display_label} contact-count {qualifier}")
    return _finish(fig, ax, grid_axis="both")


def plot_catalog_state_occupancy(
    result: AtomicConnectivityStatistics
    | FrameworkTopologyStatistics
    | TopologyStatistics,
    *,
    branch: TopologyBranch = "atomic",
    ax: Axes | None = None,
    probability_unit: ProbabilityUnit = "fraction",
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot state or topology-class occupancy probabilities."""
    stats = _branch(result, branch)
    scale, ylabel = _probability_scale(probability_unit)
    occupancy = stats.catalog_occupancy
    fig, ax = _new_axes(ax)
    ids = np.arange(occupancy.n_states)
    ax.bar(ids, occupancy.state_probabilities * scale)
    ax.set_xlabel("Atomic state ID" if branch == "atomic" else "Framework class ID")
    ax.set_ylabel(ylabel)
    ax.set_title(title or f"{branch.capitalize()} catalog occupancy")
    if occupancy.n_states <= 30:
        ax.set_xticks(ids)
    return _finish(fig, ax, grid_axis="y")


def plot_catalog_state_timeline(
    result: AtomicConnectivityStatistics
    | FrameworkTopologyStatistics
    | TopologyStatistics,
    *,
    branch: TopologyBranch = "atomic",
    ax: Axes | None = None,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot the exact catalog assignment for every trajectory frame or ensemble sample."""
    stats = _branch(result, branch)
    fig, ax = _new_axes(ax)
    ax.step(
        stats.axis.x_values,
        stats.catalog_occupancy.frame_to_state_id,
        where="post",
    )
    ax.set_xlabel(stats.axis.x_label)
    ax.set_ylabel("Atomic state ID" if branch == "atomic" else "Framework class ID")
    suffix = (
        "timeline"
        if stats.axis.frame_semantics.value == "trajectory"
        else "assignment by sample"
    )
    ax.set_title(title or f"{branch.capitalize()} catalog {suffix}")
    return _finish(fig, ax, grid_axis="both")


def _state_temporal(
    result: AtomicConnectivityStatistics
    | FrameworkTopologyStatistics
    | TopologyStatistics,
    branch: TopologyBranch,
) -> StateTransitionStatistics:
    stats = _branch(result, branch)
    temporal = stats.temporal_statistics
    if temporal is None:
        raise ValueError(
            "Detailed temporal statistics are unavailable for this result."
        )
    return temporal.state_statistics


def plot_transition_raster(
    result: AtomicConnectivityStatistics
    | FrameworkTopologyStatistics
    | TopologyStatistics,
    *,
    branch: TopologyBranch = "atomic",
    ax: Axes | None = None,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot exact changed-state boundaries as a one-row event raster."""
    temporal = _state_temporal(result, branch)
    fig, ax = _new_axes(ax, figsize=(7.2, 2.3))
    positions = np.asarray(
        [event.result_position_after for event in temporal.transition_events],
        dtype=np.int64,
    )
    x = temporal.axis.x_values[positions] if positions.size else np.asarray([])
    if x.size:
        ax.eventplot(x, orientation="horizontal", lineoffsets=0.0, linelengths=0.8)
    ax.set_yticks([])
    ax.set_xlabel(temporal.axis.x_label)
    ax.set_title(title or f"{branch.capitalize()} state-transition raster")
    return _finish(fig, ax, grid_axis="x")


def plot_transition_matrix(
    result: AtomicConnectivityStatistics
    | FrameworkTopologyStatistics
    | TopologyStatistics,
    *,
    branch: TopologyBranch = "atomic",
    changed_only: bool = True,
    ax: Axes | None = None,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot the state-to-state adjacency or changed-transition count matrix."""
    temporal = _state_temporal(result, branch)
    matrix = (
        temporal.changed_count_matrix
        if changed_only
        else temporal.adjacent_count_matrix
    )
    fig, ax = _new_axes(ax, figsize=(5.6, 4.8))
    image = ax.imshow(matrix, origin="lower", aspect="auto")
    fig.colorbar(image, ax=ax, label="Boundary count")
    ax.set_xlabel("Target state ID")
    ax.set_ylabel("Source state ID")
    kind = "Changed-state" if changed_only else "Adjacent-state"
    ax.set_title(title or f"{kind} matrix ({branch})")
    return _finish(fig, ax)


def plot_dwell_distribution(
    result: AtomicConnectivityStatistics
    | FrameworkTopologyStatistics
    | TopologyStatistics,
    *,
    branch: TopologyBranch = "atomic",
    ax: Axes | None = None,
    probability_unit: ProbabilityUnit = "fraction",
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot the exact PMF of catalog residence lengths in frames."""
    temporal = _state_temporal(result, branch)
    scale, ylabel = _probability_scale(probability_unit)
    distribution = temporal.dwell_frame_distribution
    fig, ax = _new_axes(ax)
    ax.bar(distribution.support, distribution.probabilities * scale)
    ax.set_xlabel("Residence length (frames)")
    ax.set_ylabel(ylabel)
    ax.set_title(
        title or f"{branch.capitalize()} catalog residence-length distribution"
    )
    return _finish(fig, ax, grid_axis="y")


def plot_contact_occupancy_distribution(
    result: AtomicConnectivityStatistics | TopologyStatistics,
    left: int | str,
    right: int | str,
    *,
    ax: Axes | None = None,
    bins: int = 20,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot the distribution of gauge-invariant atom-pair contact occupancies."""
    stats = _atomic_branch(result).pair(left, right)
    display_label = _requested_pair_label(left, right)
    if stats.contact_occupancies is None:
        raise ValueError("Contact occupancy statistics were disabled.")
    probabilities = np.asarray([item.probability for item in stats.contact_occupancies])
    fig, ax = _new_axes(ax)
    if probabilities.size:
        ax.hist(probabilities, bins=bins, range=(0.0, 1.0))
    ax.set_xlabel("Contact occupancy probability")
    ax.set_ylabel("Contact count")
    ax.set_title(title or f"{display_label} contact-occupancy distribution")
    return _finish(fig, ax, grid_axis="y")


def plot_graph_descriptor_timeseries(
    result: FrameworkTopologyStatistics | TopologyStatistics,
    descriptor: str,
    *,
    ax: Axes | None = None,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot one completed framework graph descriptor over frames or samples."""
    framework = _framework_branch(result)
    stats = framework.descriptor(descriptor)
    fig, ax = _new_axes(ax)
    ax.plot(framework.axis.x_values, stats.series.values)
    ax.set_xlabel(framework.axis.x_label)
    ax.set_ylabel(descriptor.replace("_", " ").capitalize())
    ax.set_title(title or f"Framework {descriptor.replace('_', ' ')}")
    return _finish(fig, ax, grid_axis="both")


def plot_cross_layer_boundary_counts(
    result: TopologyStatistics,
    *,
    ax: Axes | None = None,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot counts of stable, atomic-only, framework-only, and coupled boundaries."""
    if not isinstance(result, TopologyStatistics):
        raise TypeError("result must be TopologyStatistics.")
    boundaries = result.boundary_statistics
    if boundaries is None:
        raise ValueError("Cross-layer boundary statistics are unavailable.")
    labels = ["Stable", "Atomic only", "Framework only", "Coupled"]
    values = [
        boundaries.n_stable_boundaries,
        boundaries.n_atomic_only_boundaries,
        boundaries.n_framework_only_boundaries,
        boundaries.n_coupled_boundaries,
    ]
    fig, ax = _new_axes(ax)
    bars = ax.bar(labels, values)
    ax.bar_label(bars, labels=[str(value) for value in values], padding=3)
    ax.set_ylabel("Boundary count")
    ax.set_title(title or "Cross-layer boundary classification")
    ax.tick_params(axis="x", rotation=20)
    return _finish(fig, ax, grid_axis="y")


def plot_cross_layer_contingency(
    result: TopologyStatistics,
    *,
    ax: Axes | None = None,
    probability: bool = False,
    title: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot the atomic-state/framework-class contingency matrix."""
    if not isinstance(result, TopologyStatistics):
        raise TypeError("result must be TopologyStatistics.")
    matrix = (
        result.contingency.probability_matrix
        if probability
        else result.contingency.frame_count_matrix
    )
    fig, ax = _new_axes(ax, figsize=(5.6, 5.0))
    image = ax.imshow(matrix, origin="lower", aspect="auto")
    fig.colorbar(image, ax=ax, label="Probability" if probability else "Frame count")
    ax.set_xlabel("Framework class ID")
    ax.set_ylabel("Atomic state ID")
    ax.set_title(title or "Atomic-state/framework-class contingency")
    return _finish(fig, ax)


__all__ = [
    "ProbabilityUnit",
    "TopologyBranch",
    "plot_pair_count_distribution",
    "plot_pair_count_timeseries",
    "plot_catalog_state_occupancy",
    "plot_catalog_state_timeline",
    "plot_transition_raster",
    "plot_transition_matrix",
    "plot_dwell_distribution",
    "plot_contact_occupancy_distribution",
    "plot_graph_descriptor_timeseries",
    "plot_cross_layer_boundary_counts",
    "plot_cross_layer_contingency",
]
