"""TS5 tests for topology-statistics plotting and stable table export."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkMapping,
    FrameworkPathRule,
    TopologyCatalogOptions,
    TopologyStatistics,
    build_topology_catalog,
    build_topology_statistics_tables,
    compute_atomic_connectivity,
    compute_topology_statistics,
    export_topology_statistics,
    plot_catalog_state_occupancy,
    plot_catalog_state_timeline,
    plot_contact_occupancy_distribution,
    plot_cross_layer_boundary_counts,
    plot_cross_layer_contingency,
    plot_dwell_distribution,
    plot_graph_descriptor_timeseries,
    plot_pair_count_distribution,
    plot_pair_count_timeseries,
    plot_transition_matrix,
    plot_transition_raster,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey


def _collection(n_frames: int = 5) -> AtomisticFrameCollection:
    atomic_numbers = np.asarray([14, 8, 13, 11], dtype=np.int32)
    cell = np.eye(3) * 12.0
    fractional = np.zeros((n_frames, atomic_numbers.size, 3), dtype=float)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(100, 100 + n_frames, dtype=np.int64),
        atomic_numbers=atomic_numbers,
        masses=np.ones(atomic_numbers.size),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64) * 10,
        times=np.arange(n_frames, dtype=float) * 0.1,
        cells=np.repeat(cell[None, ...], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros_like(fractional),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _result() -> TopologyStatistics:
    collection = _collection()
    bridge = (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2))
    na_contact = AtomicEdgeKey(1, 3)
    atomic = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            frame_edges={
                0: bridge,
                1: (*bridge, na_contact),
                2: (*bridge, na_contact),
                3: bridge,
                4: (*bridge, na_contact),
            }
        ),
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker", "Na": "spectator"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
    )
    framework = build_topology_catalog(
        collection,
        atomic,
        mapping,
        catalog_options=TopologyCatalogOptions(mode="catalog"),
    )
    return compute_topology_statistics(
        atomic,
        framework,
        steps=collection.steps,
        times=collection.times,
        time_unit="ps",
    )


def test_atomic_distribution_and_series_plots_use_completed_values() -> None:
    result = _result()
    fig, ax = plot_pair_count_distribution(result, "Na", "O")
    assert len(ax.patches) == 2
    np.testing.assert_allclose([patch.get_height() for patch in ax.patches], [0.4, 0.6])
    plt.close(fig)

    fig, ax = plot_pair_count_timeseries(result, "Na", "O")
    np.testing.assert_array_equal(ax.lines[0].get_ydata(), [0, 1, 1, 0, 1])
    assert ax.get_xlabel() == "Time (ps)"
    plt.close(fig)


def test_catalog_temporal_and_framework_plots() -> None:
    result = _result()
    functions = [
        lambda: plot_catalog_state_occupancy(result, branch="atomic"),
        lambda: plot_catalog_state_timeline(result, branch="framework"),
        lambda: plot_transition_raster(result, branch="atomic"),
        lambda: plot_transition_matrix(result, branch="atomic"),
        lambda: plot_dwell_distribution(result, branch="atomic"),
        lambda: plot_graph_descriptor_timeseries(result, "edge_count"),
        lambda: plot_cross_layer_boundary_counts(result),
        lambda: plot_cross_layer_contingency(result),
    ]
    for factory in functions:
        fig, ax = factory()
        assert fig is ax.figure
        plt.close(fig)


def test_contact_occupancy_distribution_and_figure_export(tmp_path: Path) -> None:
    result = _result()
    fig, _ = plot_contact_occupancy_distribution(result, "Na", "O", bins=5)
    for suffix in ("png", "svg", "pdf"):
        path = tmp_path / f"occupancy.{suffix}"
        fig.savefig(path)
        assert path.stat().st_size > 0
    plt.close(fig)


def test_table_builder_and_export_manifest(tmp_path: Path) -> None:
    result = _result()
    tables = build_topology_statistics_tables(result)
    names = {table.name for table in tables}
    assert {
        "frame_axis",
        "atomic_pair_count_distribution",
        "framework_descriptor_series",
        "cross_layer_contingency",
        "cross_layer_boundaries",
    } <= names
    assert len(names) == len(tables)

    manifest = export_topology_statistics(result, tmp_path, prefix="case")
    assert manifest.json_path is not None and manifest.json_path.exists()
    assert manifest.csv_paths
    payload = json.loads(manifest.json_path.read_text())
    restored = TopologyStatistics.from_dict(payload)
    assert restored.digest == result.digest
    pair_path = tmp_path / "case_atomic_pair_count_distribution.csv"
    with pair_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert any(row["species_pair"] == "O-Na" for row in rows)


def test_export_refuses_overwrite_by_default(tmp_path: Path) -> None:
    result = _result()
    export_topology_statistics(result, tmp_path, prefix="case")
    with pytest.raises(FileExistsError):
        export_topology_statistics(result, tmp_path, prefix="case")
    export_topology_statistics(result, tmp_path, prefix="case", overwrite=True)
