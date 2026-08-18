"""Tests for the optional interactive Plotly graph renderer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mdstats import (
    CanonicalCellDisplay,
    ConnectivityScope,
    DecoratedGraphView,
    DistanceConnectivity,
    ExpandedCellDisplay,
    Graph3DRenderOptions,
    GraphFocus,
    GraphStyle,
    LocalUnwrappedDisplay,
    PairCutoffRegistry,
    compute_atomic_connectivity,
    plot_atomic_connectivity_3d,
    plot_decorated_graph_3d,
    read_structure,
)
from mdstats.plotting import GraphStyleError


def simple_view() -> DecoratedGraphView:
    return DecoratedGraphView(
        node_keys=(0, 1),
        edge_keys=("bond",),
        edge_endpoints=np.array([[0, 1]], dtype=np.int64),
        node_positions_3d=np.array([[9.5, 0.0, 0.0], [0.5, 0.0, 0.0]]),
        edge_image_shifts=np.array([[1, 0, 0]], dtype=np.int64),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
        node_attributes={"symbol": ("Si", "O"), "degree": np.array([1, 1])},
        edge_attributes={"species_pair": (("O", "Si"),)},
    )


def test_3d_options_validate() -> None:
    with pytest.raises(GraphStyleError):
        Graph3DRenderOptions(width=0)
    with pytest.raises(GraphStyleError):
        Graph3DRenderOptions(camera_eye=(0.0, 0.0, 0.0))
    with pytest.raises(GraphStyleError):
        Graph3DRenderOptions(gradient_segments=1)


def test_canonical_3d_render_hover_and_html(tmp_path: Path) -> None:
    result = plot_decorated_graph_3d(
        simple_view(),
        periodic=CanonicalCellDisplay(),
        style=GraphStyle.atomic_default(),
        options=Graph3DRenderOptions(show_axes=True),
    )
    assert len(result.rendered_node_keys) == 3
    assert len(result.rendered_edge_keys) == 1
    assert result.render_metadata["cell_line_count"] == 12
    assert result.node_trace_indices
    assert result.edge_trace_indices
    assert result.hover_trace_indices["edge_midpoints"]
    html = result.to_html(full_html=False)
    assert "Plotly.newPlot" in html
    output = tmp_path / "graph.html"
    result.write_html(output)
    assert output.stat().st_size > 1000


def test_local_and_expanded_3d_geometry() -> None:
    local = plot_decorated_graph_3d(
        simple_view(),
        periodic=LocalUnwrappedDisplay(0),
        style=GraphStyle.atomic_default(),
        options=Graph3DRenderOptions(cell_mode="none"),
    )
    distance = np.linalg.norm(
        local.periodic_view.graph.node_positions_3d[1]
        - local.periodic_view.graph.node_positions_3d[0]
    )
    assert distance == pytest.approx(1.0)
    expanded = plot_decorated_graph_3d(
        simple_view(),
        periodic=ExpandedCellDisplay(((0, 1), (0, 0), (0, 0))),
        style=GraphStyle.atomic_default(),
        options=Graph3DRenderOptions(cell_mode="outer_boundary"),
    )
    assert expanded.periodic_view.graph.n_edges == 2
    assert expanded.render_metadata["cell_line_count"] == 12


def test_relaxed_na_lta_3d_system_integration(tmp_path: Path) -> None:
    structure = Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR"
    collection = read_structure(structure, format="vasp")
    result = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.0, ("Al", "O"): 2.0}
            ),
            scope=ConnectivityScope.from_selection(
                included_atom_indices=tuple(range(144))
            ),
        ),
    )
    state = result.states[0]
    assert state.n_active_atoms == 144
    assert state.n_edges == 192
    rendered = plot_atomic_connectivity_3d(
        collection,
        result,
        frame_index=0,
        periodic=LocalUnwrappedDisplay(0, hop_radius=4),
        style=GraphStyle.atomic_default(),
        focus=GraphFocus(center_node_keys=(0,), hop_radius=4),
        options=Graph3DRenderOptions(
            title="Relaxed Na-LTA local framework connectivity",
            cell_mode="reference",
            camera_projection="orthographic",
        ),
    )
    assert rendered.periodic_view.graph.n_nodes > 0
    assert rendered.periodic_view.graph.n_edges > 0
    assert all(
        key.source_node_key in set(range(144)) for key in rendered.rendered_node_keys
    )
    output = tmp_path / "na_lta_local.html"
    rendered.write_html(output)
    assert output.stat().st_size > 10_000


def test_plotly_optional_dependency_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The base package must fail clearly when the optional backend is absent."""
    import builtins
    import sys

    real_import = builtins.__import__
    plotly_modules = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith("plotly")
    }
    for name in plotly_modules:
        monkeypatch.delitem(sys.modules, name, raising=False)

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "plotly" or name.startswith("plotly."):
            raise ImportError("plotly intentionally unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    from mdstats.plotting import GraphOptionalDependencyError

    with pytest.raises(GraphOptionalDependencyError, match="mdstats\\[interactive\\]"):
        plot_decorated_graph_3d(simple_view())


def test_directed_parallel_and_self_loop_guards() -> None:
    """Ambiguous straight-line graph features require explicit user intent."""
    from mdstats.plotting import GraphUnsupportedFeatureError

    directed = DecoratedGraphView(
        node_keys=(0, 1),
        edge_keys=("directed",),
        edge_endpoints=np.array([[0, 1]], dtype=np.int64),
        node_positions_3d=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        directed=True,
    )
    with pytest.raises(GraphUnsupportedFeatureError, match="Directed graphs"):
        plot_decorated_graph_3d(directed)
    with pytest.warns(RuntimeWarning, match="without 3-D arrowheads"):
        rendered = plot_decorated_graph_3d(
            directed,
            options=Graph3DRenderOptions(
                directed_edge_mode="line_only",
                cell_mode="none",
            ),
        )
    assert rendered.periodic_view.graph.directed

    parallel = DecoratedGraphView(
        node_keys=(0, 1),
        edge_keys=("a", "b"),
        edge_endpoints=np.array([[0, 1], [0, 1]], dtype=np.int64),
        node_positions_3d=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        multigraph=True,
    )
    with pytest.raises(GraphUnsupportedFeatureError, match="Parallel display edges"):
        plot_decorated_graph_3d(parallel)
    with pytest.warns(RuntimeWarning, match="overlap exactly"):
        rendered_parallel = plot_decorated_graph_3d(
            parallel,
            options=Graph3DRenderOptions(
                allow_parallel_overlap=True,
                cell_mode="none",
            ),
        )
    assert rendered_parallel.periodic_view.graph.n_edges == 2

    self_loop = DecoratedGraphView(
        node_keys=(0,),
        edge_keys=("loop",),
        edge_endpoints=np.array([[0, 0]], dtype=np.int64),
        node_positions_3d=np.array([[0.0, 0.0, 0.0]]),
    )
    with pytest.raises(GraphUnsupportedFeatureError, match="Self-loop"):
        plot_decorated_graph_3d(self_loop)


def test_segmented_gradient_mode_is_explicit() -> None:
    with pytest.warns(RuntimeWarning, match="Equal-aspect"):
        rendered = plot_decorated_graph_3d(
            simple_view(),
            style=GraphStyle.atomic_default(),
            options=Graph3DRenderOptions(
                edge_color_mode="segmented_gradient",
                gradient_segments=5,
                cell_mode="none",
            ),
        )
    assert rendered.render_metadata["edge_color_mode"] == "segmented_gradient"
    assert rendered.render_metadata["edge_line_primitives"] == 5
