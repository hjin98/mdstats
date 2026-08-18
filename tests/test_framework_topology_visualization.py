"""Framework-topology visualization adapter and wrapper tests."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    CanonicalCellDisplay,
    ConnectivityScope,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkGraphDisplayMode,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkPathSegmentKey,
    Graph2DRenderOptions,
    Graph3DRenderOptions,
    GraphLayoutOptions,
    GraphStyle,
    LocalUnwrappedDisplay,
    NodeDisplayMode,
    PairCutoffRegistry,
    build_framework_topology,
    compute_atomic_connectivity,
    graph_view_from_framework_topology,
    plot_framework_topology_2d,
    plot_framework_topology_3d,
    read_structure,
)
from mdstats.plotting import GraphAdapterError, GraphStyleError


def make_collection(
    atomic_numbers: list[int],
    positions: np.ndarray,
    *,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> AtomisticFrameCollection:
    numbers = np.asarray(atomic_numbers, dtype=np.int32)
    cell = np.eye(3) * 10.0
    xyz = np.asarray(positions, dtype=float)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=numbers,
        masses=np.ones(numbers.size),
        pbc=np.asarray(pbc, dtype=bool),
        steps=None,
        times=None,
        cells=cell[None, ...],
        origins=np.zeros((1, 3)),
        fractional_positions=(xyz @ np.linalg.inv(cell))[None, ...],
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def tot_mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),
        ),
        name="T-O-T visualization mapping",
    )


def build_distance_topology(
    collection: AtomisticFrameCollection,
    *,
    include_atoms: tuple[int, ...] | None = None,
):
    cutoffs = PairCutoffRegistry.from_mapping({("Si", "O"): 2.0, ("Al", "O"): 2.0})
    definition = DistanceConnectivity(
        cutoffs=cutoffs,
        scope=(
            ConnectivityScope.from_selection(included_atom_indices=include_atoms)
            if include_atoms is not None
            else ConnectivityScope.all()
        ),
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
    return build_framework_topology(state, tot_mapping())


def test_projected_and_atomic_path_views_preserve_authoritative_identity() -> None:
    collection = make_collection(
        [14, 8, 13],
        np.asarray([[1.0, 1.0, 1.0], [2.0, 1.0, 1.0], [3.0, 1.0, 1.0]]),
    )
    topology = build_distance_topology(collection)

    projected = graph_view_from_framework_topology(collection, topology, frame_index=0)
    assert projected.n_nodes == 2
    assert projected.n_edges == 1
    assert projected.node_keys == tuple(int(x) for x in topology.vertex_atom_indices)
    assert projected.edge_keys == topology.edge_keys
    assert projected.multigraph
    assert projected.metadata["display_mode"] == "projected"
    assert projected.edge_attributes["atomic_path_indices"] == ((0, 1, 2),)
    assert projected.edge_attributes["edge_kind"] == ("oxygen_bridge",)

    diagnostic = graph_view_from_framework_topology(
        collection,
        topology,
        frame_index=0,
        display_mode=FrameworkGraphDisplayMode.ATOMIC_PATHS,
    )
    assert diagnostic.n_nodes == 3
    assert diagnostic.n_edges == 2
    assert diagnostic.multigraph
    assert diagnostic.node_attributes["framework_role"] == (
        "vertex",
        "linker",
        "vertex",
    )
    assert set(diagnostic.edge_attributes["segment_kind"]) == {
        "vertex_linker",
        "linker_vertex",
    }
    first_key = diagnostic.edge_keys[0]
    assert isinstance(first_key, FrameworkPathSegmentKey)
    assert FrameworkPathSegmentKey.from_dict(first_key.to_dict()) == first_key


def test_periodic_path_shift_matches_retained_atomic_path() -> None:
    collection = make_collection(
        [14, 8, 13],
        np.asarray([[9.2, 0.0, 0.0], [0.0, 0.0, 0.0], [0.8, 0.0, 0.0]]),
    )
    topology = build_distance_topology(collection)
    projected = graph_view_from_framework_topology(collection, topology, frame_index=0)
    np.testing.assert_array_equal(projected.edge_image_shifts, [[1, 0, 0]])
    vector = (
        projected.node_positions_3d[1]
        + projected.edge_image_shifts[0] @ projected.cell
        - projected.node_positions_3d[0]
    )
    assert np.linalg.norm(vector) == pytest.approx(1.6)

    diagnostic = graph_view_from_framework_topology(
        collection,
        topology,
        frame_index=0,
        display_mode="atomic_paths",
    )
    np.testing.assert_array_equal(
        np.sum(diagnostic.edge_image_shifts, axis=0), [1, 0, 0]
    )


def test_asymmetric_path_visualization_preserves_both_traversal_signatures() -> None:
    collection = make_collection(
        [14, 8, 16, 13],
        np.asarray(
            [
                [1.0, 1.0, 1.0],
                [2.0, 1.0, 1.0],
                [3.0, 1.0, 1.0],
                [4.0, 1.0, 1.0],
            ]
        ),
    )
    cutoffs = PairCutoffRegistry.from_mapping(
        {("Si", "O"): 1.2, ("O", "S"): 1.2, ("S", "Al"): 1.2}
    )
    state = compute_atomic_connectivity(
        collection, DistanceConnectivity(cutoffs=cutoffs)
    ).states[0]
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker", "S": "linker"},
        path_rules=(
            FrameworkPathRule.from_symbols(
                "Si-O-S-Al",
                ("O", "S"),
                endpoint_symbols=("Si", "Al"),
                edge_kind="asymmetric_bridge",
            ),
        ),
    )
    topology = build_framework_topology(state, mapping)
    projected = graph_view_from_framework_topology(collection, topology, frame_index=0)
    assert projected.directed is False
    assert projected.metadata["edge_semantics"] == (
        "undirected adjacency with orientation-aware path decoration"
    )
    assert projected.edge_attributes["canonical_path_symbols"] == (
        ("Si", "O", "S", "Al"),
    )
    assert projected.edge_attributes["reverse_path_symbols"] == (
        ("Al", "S", "O", "Si"),
    )
    np.testing.assert_array_equal(
        projected.edge_attributes["orientation_aware"], [True]
    )

    diagnostic = graph_view_from_framework_topology(
        collection, topology, frame_index=0, display_mode="atomic_paths"
    )
    assert set(diagnostic.edge_attributes["parent_canonical_path_symbols"]) == {
        ("Si", "O", "S", "Al")
    }
    assert set(diagnostic.edge_attributes["parent_reverse_path_symbols"]) == {
        ("Al", "S", "O", "Si")
    }


def test_parallel_paths_remain_a_multigraph() -> None:
    collection = make_collection(
        [14, 8, 8, 13],
        np.asarray(
            [
                [1.0, 1.0, 1.0],
                [2.0, 0.7, 1.0],
                [2.0, 1.3, 1.0],
                [3.0, 1.0, 1.0],
            ]
        ),
    )
    topology = build_distance_topology(collection)
    assert topology.n_edges == 2
    projected = graph_view_from_framework_topology(collection, topology, frame_index=0)
    np.testing.assert_array_equal(
        projected.edge_attributes["parallel_multiplicity"], [2, 2]
    )
    np.testing.assert_array_equal(projected.edge_attributes["parallel_rank"], [0, 1])
    diagnostic = graph_view_from_framework_topology(
        collection, topology, frame_index=0, display_mode="atomic_paths"
    )
    assert diagnostic.n_nodes == 4
    assert diagnostic.n_edges == 4
    assert len(set(diagnostic.edge_keys)) == 4


def test_collection_topology_mismatch_is_rejected() -> None:
    collection = make_collection(
        [14, 8, 13],
        np.asarray([[1.0, 1.0, 1.0], [2.0, 1.0, 1.0], [3.0, 1.0, 1.0]]),
    )
    topology = build_distance_topology(collection)
    wrong_species = make_collection(
        [14, 16, 13],
        np.asarray([[1.0, 1.0, 1.0], [2.0, 1.0, 1.0], [3.0, 1.0, 1.0]]),
    )
    with pytest.raises(GraphAdapterError, match="atomic numbers"):
        graph_view_from_framework_topology(wrong_species, topology, frame_index=0)


def test_framework_style_presets_are_role_and_edge_kind_aware() -> None:
    projected = GraphStyle.framework_default()
    diagnostic = GraphStyle.framework_default(diagnostic=True)
    assert projected.edge_default.color_mode == "constant"
    assert projected.edge_default.width > diagnostic.edge_default.width
    assert any(rule.attribute == "edge_kind" for rule in projected.edge_rules)
    assert any(rule.attribute == "framework_role" for rule in diagnostic.node_rules)


def test_framework_node_display_modes_are_consistent_across_renderers() -> None:
    collection = make_collection(
        [14, 8, 13],
        np.asarray([[1.0, 1.0, 1.0], [2.0, 1.0, 1.0], [3.0, 1.0, 1.0]]),
    )
    topology = build_distance_topology(collection)

    dot_style = GraphStyle.framework_default(
        node_display_mode=NodeDisplayMode.DOTS, node_dot_size=16.0
    )
    dots_2d = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        style=dot_style,
        layout=GraphLayoutOptions(method="physical", projection="xy"),
        options=Graph2DRenderOptions(show_axes=False),
    )
    assert dots_2d.style_metadata["node_display_mode"] == "dots"
    assert dots_2d.artist_groups["nodes"]
    assert all(
        np.allclose(artist.get_sizes(), [16.0])
        for artist in dots_2d.artist_groups["nodes"]
    )

    hidden_style = GraphStyle.framework_default(node_display_mode="hidden")
    hidden_2d = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        style=hidden_style,
        layout=GraphLayoutOptions(method="physical", projection="xy"),
        options=Graph2DRenderOptions(show_axes=False),
    )
    assert hidden_2d.rendered_node_keys == tuple(
        int(x) for x in topology.vertex_atom_indices
    )
    assert hidden_2d.artist_groups["nodes"] == ()
    assert hidden_2d.artist_groups["ghost_nodes"] == ()
    assert hidden_2d.artist_groups["edges"]

    dots_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        style=dot_style,
        periodic=CanonicalCellDisplay(),
        options=Graph3DRenderOptions(cell_mode="none", edge_color_mode="constant"),
    )
    assert dots_3d.node_trace_indices
    assert dots_3d.style_metadata["node_display_mode"] == "dots"
    marker_sizes = [
        float(trace.marker.size)
        for trace in dots_3d.figure.data
        if getattr(trace, "mode", None) in {"markers", "markers+text"}
        and trace.name != "Edge metadata"
    ]
    assert marker_sizes and set(marker_sizes) == {4.0}

    hidden_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        style=hidden_style,
        periodic=CanonicalCellDisplay(),
        options=Graph3DRenderOptions(cell_mode="none", edge_color_mode="constant"),
    )
    assert hidden_3d.rendered_node_keys
    assert not hidden_3d.node_trace_indices
    assert hidden_3d.edge_trace_indices
    assert hidden_3d.render_metadata["node_display_mode"] == "hidden"


def test_node_display_mode_validation() -> None:
    with pytest.raises(GraphStyleError, match="node_display_mode"):
        GraphStyle(node_display_mode="not-a-mode")
    with pytest.raises(GraphStyleError, match="node_dot_size"):
        GraphStyle(node_dot_size=0.0)


def test_relaxed_na_lta_framework_visualization_integration(tmp_path: Path) -> None:
    structure = Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR"
    collection = read_structure(structure, format="vasp")
    topology = build_distance_topology(collection, include_atoms=tuple(range(144)))
    assert topology.n_vertices == 48
    assert topology.n_edges == 96
    np.testing.assert_array_equal(topology.degree, np.full(48, 4))

    projected = graph_view_from_framework_topology(collection, topology, frame_index=0)
    assert projected.n_nodes == 48
    assert projected.n_edges == 96
    assert set(projected.node_attributes["symbol"]) == {"Si", "Al"}
    assert set(projected.edge_attributes["edge_kind"]) == {"oxygen_bridge"}

    diagnostic = graph_view_from_framework_topology(
        collection, topology, frame_index=0, display_mode="atomic_paths"
    )
    assert diagnostic.n_nodes == 144
    assert diagnostic.n_edges == 192
    assert Counter(diagnostic.node_attributes["framework_role"]) == {
        "vertex": 48,
        "linker": 96,
    }
    assert "Na" not in set(diagnostic.node_attributes["symbol"])

    rendered_2d = plot_framework_topology_2d(
        collection,
        topology,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        options=Graph2DRenderOptions(show_axes=False),
    )
    png = tmp_path / "framework_projected.png"
    rendered_2d.figure.savefig(png, dpi=120)
    assert png.stat().st_size > 10_000

    rendered_3d = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        periodic=LocalUnwrappedDisplay(0, hop_radius=3),
        options=Graph3DRenderOptions(cell_mode="reference", edge_color_mode="constant"),
    )
    html = tmp_path / "framework_projected.html"
    rendered_3d.write_html(html)
    assert html.stat().st_size > 10_000

    rendered_paths = plot_framework_topology_3d(
        collection,
        topology,
        frame_index=0,
        display_mode="atomic_paths",
        periodic=CanonicalCellDisplay(),
    )
    assert rendered_paths.periodic_view.graph.n_nodes >= 144
    assert rendered_paths.periodic_view.graph.n_edges == 192
