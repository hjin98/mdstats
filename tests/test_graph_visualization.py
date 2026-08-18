"""Tests for the generic graph view, 2-D renderer, and atomic adapter."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from mdstats import (
    AtomisticFrameCollection,
    ConnectivityScope,
    DecoratedGraphView,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    Graph2DRenderOptions,
    GraphFilter,
    GraphFocus,
    GraphLayoutOptions,
    GraphStyle,
    HystereticDistanceConnectivity,
    PairCutoffRegistry,
    compute_atomic_connectivity,
    graph_view_from_atomic_connectivity,
    graph_view_from_connectivity_transition,
    plot_atomic_connectivity_2d,
    plot_connectivity_transition_2d,
    plot_decorated_graph_2d,
    read_structure,
)
from mdstats.plotting import AttributeSelection, GraphViewValidationError


def make_collection(
    positions: np.ndarray,
    *,
    atomic_numbers: np.ndarray,
    semantics: FrameSemantics = FrameSemantics.ENSEMBLE,
) -> AtomisticFrameCollection:
    positions = np.asarray(positions, dtype=float)
    if positions.ndim == 2:
        positions = positions[None, ...]
    n_frames, n_atoms, _ = positions.shape
    cells = np.repeat((np.eye(3) * 10.0)[None, ...], n_frames, axis=0)
    fractional = positions / 10.0
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=(
            np.arange(n_frames, dtype=np.int64)
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        times=(
            np.arange(n_frames, dtype=float)
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=(
            np.zeros((n_frames, n_atoms, 3))
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source=(
                "native" if semantics is FrameSemantics.TRAJECTORY else "unavailable"
            ),
            coordinate_normalization="synthetic",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_graph_view_is_defensively_immutable_and_validates_duplicates() -> None:
    endpoints = np.array([[0, 1]], dtype=np.int64)
    positions = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    attrs = {"symbol": np.array(["Si", "O"])}
    view = DecoratedGraphView(
        node_keys=(10, 11),
        edge_keys=((10, 11),),
        edge_endpoints=endpoints,
        node_positions_3d=positions,
        node_attributes=attrs,
    )
    endpoints[0, 0] = 1
    positions[0, 0] = 99.0
    attrs["symbol"][0] = "X"
    np.testing.assert_array_equal(view.edge_endpoints, [[0, 1]])
    np.testing.assert_allclose(view.node_positions_3d[0], [0.0, 0.0, 0.0])
    assert view.node_attributes["symbol"][0] == "Si"
    assert not view.edge_endpoints.flags.writeable
    with pytest.raises(GraphViewValidationError):
        DecoratedGraphView(
            node_keys=(0, 0),
            edge_keys=(),
            edge_endpoints=np.empty((0, 2), dtype=np.int64),
        )


def test_focus_precedes_attribute_filter_and_preserves_keys() -> None:
    view = DecoratedGraphView(
        node_keys=(0, 1, 2, 3),
        edge_keys=("a", "b", "c"),
        edge_endpoints=np.array([[0, 1], [1, 2], [2, 3]]),
        node_attributes={"kind": ("keep", "hide", "keep", "keep")},
    )
    result = plot_decorated_graph_2d(
        view,
        layout=GraphLayoutOptions(method="spring", seed=3),
        focus=GraphFocus(center_node_keys=(0,), hop_radius=2),
        graph_filter=GraphFilter(
            node_attribute_selections=(
                AttributeSelection("kind", exclude_values=("hide",)),
            )
        ),
        options=Graph2DRenderOptions(show_axes=False),
    )
    assert result.rendered_node_keys == (0, 2)
    assert result.rendered_edge_keys == ()


def test_periodic_atomic_adapter_reconstructs_frame_display_shift() -> None:
    collection = make_collection(
        np.array([[9.5, 0.0, 0.0], [0.5, 0.0, 0.0]]),
        atomic_numbers=np.array([14, 8]),
    )
    definition = DistanceConnectivity(
        PairCutoffRegistry.from_mapping({("Si", "O"): 1.5})
    )
    result = compute_atomic_connectivity(collection, definition)
    state = result.states[0]
    assert state.edge_keys[0].image_shift == (0, 0, 0)
    view = graph_view_from_atomic_connectivity(collection, result, frame_index=0)
    np.testing.assert_array_equal(view.edge_image_shifts, [[1, 0, 0]])
    render = plot_atomic_connectivity_2d(
        collection,
        result,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="xy"),
        options=Graph2DRenderOptions(show_axes=False),
    )
    assert np.linalg.norm(
        render.edge_paths_2d[0][1] - render.edge_paths_2d[0][0]
    ) == pytest.approx(1.0)


def test_spring_layout_is_deterministic() -> None:
    view = DecoratedGraphView(
        node_keys=(0, 1, 2),
        edge_keys=(0, 1),
        edge_endpoints=np.array([[0, 1], [1, 2]]),
    )
    options = GraphLayoutOptions(method="spring", seed=17)
    first = plot_decorated_graph_2d(view, layout=options)
    second = plot_decorated_graph_2d(view, layout=options)
    np.testing.assert_allclose(first.node_positions_2d, second.node_positions_2d)


def test_transition_adapter_and_renderer_classify_added_removed_edges() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.8, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        ]
    )
    collection = make_collection(
        positions,
        atomic_numbers=np.array([14, 8]),
        semantics=FrameSemantics.TRAJECTORY,
    )
    result = compute_atomic_connectivity(
        collection,
        HystereticDistanceConnectivity(
            formation_cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 1.2}),
            breaking_cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 1.6}),
        ),
    )
    first = graph_view_from_connectivity_transition(collection, result, transition_id=0)
    assert first.edge_attributes["transition_status"] == ("removed",)
    assert first.node_attributes["affected"].tolist() == [True, True]
    second = plot_connectivity_transition_2d(
        collection,
        result,
        transition_id=1,
        layout=GraphLayoutOptions(method="physical", projection="xy"),
        options=Graph2DRenderOptions(show_axes=False),
    )
    assert second.rendered_edge_keys[0][0] == "added"


def test_export_png_svg_pdf(tmp_path: Path) -> None:
    view = DecoratedGraphView(
        node_keys=(0, 1),
        edge_keys=(0,),
        edge_endpoints=np.array([[0, 1]]),
        node_positions_3d=np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 0.0]]),
    )
    result = plot_decorated_graph_2d(
        view,
        layout=GraphLayoutOptions(method="physical", projection="xy"),
    )
    for suffix in ("png", "svg", "pdf"):
        output = tmp_path / f"graph.{suffix}"
        result.figure.savefig(output)
        assert output.stat().st_size > 0


def test_relaxed_na_lta_system_integration() -> None:
    structure = Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR"
    collection = read_structure(structure, format="vasp")
    framework_indices = tuple(range(144))
    result = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.0, ("Al", "O"): 2.0}
            ),
            scope=ConnectivityScope.from_selection(
                included_atom_indices=framework_indices
            ),
        ),
    )
    state = result.states[0]
    assert collection.n_atoms == 168
    assert state.n_active_atoms == 144
    assert state.n_edges == 192
    np.testing.assert_array_equal(state.degree[:48], np.full(48, 4))
    np.testing.assert_array_equal(state.degree[48:], np.full(96, 2))
    rendered = plot_atomic_connectivity_2d(
        collection,
        result,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="pca"),
        style=GraphStyle.atomic_default(),
        options=Graph2DRenderOptions(
            show_axes=False, title="Relaxed Na-LTA framework connectivity"
        ),
    )
    assert len(rendered.rendered_node_keys) == 144
    assert len(rendered.rendered_edge_keys) == 192
    assert all(np.all(np.isfinite(path)) for path in rendered.edge_paths_2d)


def test_local_unwrapping_places_simple_periodic_pair_contiguously() -> None:
    collection = make_collection(
        np.array([[9.5, 0.0, 0.0], [0.5, 0.0, 0.0]]),
        atomic_numbers=np.array([14, 8]),
    )
    result = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(PairCutoffRegistry.from_mapping({("Si", "O"): 1.5})),
    )
    rendered = plot_atomic_connectivity_2d(
        collection,
        result,
        frame_index=0,
        layout=GraphLayoutOptions(method="physical", projection="xy"),
        options=Graph2DRenderOptions(
            show_axes=False,
            periodic_node_mode="local_unwrapped",
            show_periodic_ghosts=True,
        ),
    )
    assert rendered.periodic_metadata["node_mode"] == "local_unwrapped"
    assert rendered.periodic_metadata["periodic_edge_count"] == 0
    assert rendered.periodic_metadata["periodic_ghost_count"] == 0
    assert np.linalg.norm(
        rendered.node_positions_2d[1] - rendered.node_positions_2d[0]
    ) == pytest.approx(1.0)


def test_schematic_layout_ignores_physical_periodic_node_mode() -> None:
    collection = make_collection(
        np.array([[9.5, 0.0, 0.0], [0.5, 0.0, 0.0]]),
        atomic_numbers=np.array([14, 8]),
    )
    result = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(PairCutoffRegistry.from_mapping({("Si", "O"): 1.5})),
    )
    with pytest.warns(RuntimeWarning, match="ignored for schematic"):
        rendered = plot_atomic_connectivity_2d(
            collection,
            result,
            frame_index=0,
            layout=GraphLayoutOptions(method="spring", seed=11),
            options=Graph2DRenderOptions(periodic_node_mode="local_unwrapped"),
        )
    assert rendered.periodic_metadata["node_mode"] == "not_applicable_schematic"
    assert rendered.periodic_metadata["requested_node_mode"] == "local_unwrapped"
