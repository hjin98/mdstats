"""Generate TS5 figures and tables for the 2,000-frame Na-LTA example."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from mdstats import (
    AtomicConnectivityResult,
    TopologyCatalog,
    compute_topology_statistics,
    export_topology_statistics,
    plot_catalog_state_occupancy,
    plot_catalog_state_timeline,
    plot_cross_layer_boundary_counts,
    plot_cross_layer_contingency,
    plot_dwell_distribution,
    plot_graph_descriptor_timeseries,
    plot_pair_count_distribution,
    plot_pair_count_timeseries,
    plot_transition_raster,
)


def _save(fig, output: Path, stem: str) -> None:
    fig.savefig(output / f"{stem}.png", dpi=180, bbox_inches="tight")
    fig.savefig(output / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("atomic_catalog", type=Path)
    parser.add_argument("framework_catalog", type=Path)
    parser.add_argument("--output", type=Path, default=Path("generated"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    atomic = AtomicConnectivityResult.from_dict(
        json.loads(args.atomic_catalog.read_text(encoding="utf-8"))
    )
    framework = TopologyCatalog.from_dict(
        json.loads(args.framework_catalog.read_text(encoding="utf-8"))
    )
    n_frames = len(atomic.frame_state_ids)
    statistics = compute_topology_statistics(
        atomic,
        framework,
        steps=range(n_frames),
        times=[0.001 * frame for frame in range(n_frames)],
        time_unit="ps",
    )

    figures = {
        "na_o_count_distribution": plot_pair_count_distribution(statistics, "Na", "O"),
        "na_o_count_timeseries": plot_pair_count_timeseries(statistics, "Na", "O"),
        "si_o_count_distribution": plot_pair_count_distribution(statistics, "Si", "O"),
        "al_o_count_distribution": plot_pair_count_distribution(statistics, "Al", "O"),
        "atomic_state_occupancy": plot_catalog_state_occupancy(
            statistics, branch="atomic"
        ),
        "atomic_state_timeline": plot_catalog_state_timeline(
            statistics, branch="atomic"
        ),
        "atomic_transition_raster": plot_transition_raster(statistics, branch="atomic"),
        "atomic_dwell_distribution": plot_dwell_distribution(
            statistics, branch="atomic"
        ),
        "framework_edge_count": plot_graph_descriptor_timeseries(
            statistics, "edge_count"
        ),
        "framework_class_timeline": plot_catalog_state_timeline(
            statistics, branch="framework"
        ),
        "cross_layer_boundary_counts": plot_cross_layer_boundary_counts(statistics),
        "cross_layer_contingency": plot_cross_layer_contingency(statistics),
    }
    for stem, (fig, _) in figures.items():
        _save(fig, args.output, stem)

    export_topology_statistics(
        statistics,
        args.output / "tables",
        prefix="na_lta_300K",
        overwrite=True,
    )


if __name__ == "__main__":
    main()
