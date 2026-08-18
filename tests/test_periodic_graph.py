"""Tests for renderer-independent periodic graph materialization."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    CanonicalCellDisplay,
    DecoratedGraphView,
    ExpandedCellDisplay,
    GraphComplexityPolicy,
    LocalUnwrappedDisplay,
    PeriodicEdgeRole,
    PeriodicNodeKey,
    PeriodicNodeRole,
    prepare_periodic_graph_view,
)
from mdstats.plotting import GraphComplexityError, GraphViewValidationError


def crossing_pair() -> DecoratedGraphView:
    return DecoratedGraphView(
        node_keys=("Si", "O"),
        edge_keys=("bond",),
        edge_endpoints=np.array([[0, 1]], dtype=np.int64),
        node_positions_3d=np.array([[9.5, 0.0, 0.0], [0.5, 0.0, 0.0]]),
        edge_image_shifts=np.array([[1, 0, 0]], dtype=np.int64),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
        node_attributes={"symbol": ("Si", "O")},
        edge_attributes={"kind": ("T-O",)},
    )


def test_canonical_cell_materializes_shared_boundary_ghost() -> None:
    view = DecoratedGraphView(
        node_keys=(0, 1, 2),
        edge_keys=("a", "b"),
        edge_endpoints=np.array([[0, 2], [1, 2]], dtype=np.int64),
        node_positions_3d=np.array([[9.5, 0.0, 0.0], [9.5, 1.0, 0.0], [0.5, 0.5, 0.0]]),
        edge_image_shifts=np.array([[1, 0, 0], [1, 0, 0]], dtype=np.int64),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
        node_attributes={"symbol": ("Si", "Al", "O")},
    )
    result = prepare_periodic_graph_view(view, periodic=CanonicalCellDisplay())
    assert result.graph.n_nodes == 4
    assert result.graph.n_edges == 2
    assert result.node_roles.count(PeriodicNodeRole.GHOST) == 1
    assert result.edge_roles == (
        PeriodicEdgeRole.BOUNDARY_GHOST,
        PeriodicEdgeRole.BOUNDARY_GHOST,
    )
    ghost_key = PeriodicNodeKey(2, (1, 0, 0))
    assert result.graph.node_keys.count(ghost_key) == 1
    assert result.graph.node_attributes["symbol"][-1] == "O"
    assert not result.source_node_positions.flags.writeable


def test_local_unwrapped_pair_is_contiguous() -> None:
    result = prepare_periodic_graph_view(
        crossing_pair(), periodic=LocalUnwrappedDisplay("Si")
    )
    assert result.graph.n_nodes == 2
    assert result.node_roles == (
        PeriodicNodeRole.CANONICAL,
        PeriodicNodeRole.REPLICA,
    )
    distance = np.linalg.norm(
        result.graph.node_positions_3d[1] - result.graph.node_positions_3d[0]
    )
    assert distance == pytest.approx(1.0)
    np.testing.assert_array_equal(result.graph.edge_image_shifts, [[0, 0, 0]])


def test_winding_cycle_creates_cycle_ghost() -> None:
    view = DecoratedGraphView(
        node_keys=(0, 1, 2),
        edge_keys=("ab", "bc", "ca"),
        edge_endpoints=np.array([[0, 1], [1, 2], [2, 0]], dtype=np.int64),
        node_positions_3d=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
        edge_image_shifts=np.array([[0, 0, 0], [0, 0, 0], [1, 0, 0]], dtype=np.int64),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
    )
    result = prepare_periodic_graph_view(view, periodic=LocalUnwrappedDisplay(0))
    assert PeriodicEdgeRole.CYCLE_GHOST in result.edge_roles
    assert PeriodicNodeRole.GHOST in result.node_roles
    assert result.periodic_metadata["residual_winding_vectors"]


def test_expanded_source_cell_replication_counts_and_mappings() -> None:
    result = prepare_periodic_graph_view(
        crossing_pair(),
        periodic=ExpandedCellDisplay(((0, 1), (0, 0), (0, 0))),
    )
    assert result.graph.n_edges == 2
    assert result.graph.n_nodes == 5  # four primary images plus one outer ghost
    assert result.primary_cell_image_shifts.tolist() == [[0, 0, 0], [1, 0, 0]]
    assert result.node_roles.count(PeriodicNodeRole.GHOST) == 1
    assert result.source_edge_positions.tolist() == [0, 0]


def test_nonperiodic_image_range_and_complexity_errors() -> None:
    view = crossing_pair()
    nonperiodic = DecoratedGraphView(
        node_keys=view.node_keys,
        edge_keys=view.edge_keys,
        edge_endpoints=view.edge_endpoints,
        node_positions_3d=view.node_positions_3d,
        edge_image_shifts=np.zeros((1, 3), dtype=np.int64),
        cell=view.cell,
        pbc=np.array([False, True, True]),
    )
    with pytest.raises(GraphViewValidationError):
        prepare_periodic_graph_view(
            nonperiodic,
            periodic=ExpandedCellDisplay(((0, 1), (0, 0), (0, 0))),
        )
    with pytest.raises(GraphComplexityError):
        prepare_periodic_graph_view(
            crossing_pair(),
            periodic=ExpandedCellDisplay(((0, 10), (0, 0), (0, 0))),
            complexity_policy=GraphComplexityPolicy(max_nodes=5, max_edges=5),
        )


def test_2d_renderer_consumes_explicit_periodic_graph() -> None:
    from mdstats import GraphLayoutOptions, plot_decorated_graph_2d

    rendered = plot_decorated_graph_2d(
        crossing_pair(),
        periodic=CanonicalCellDisplay(),
        layout=GraphLayoutOptions(method="physical", projection="xy"),
    )
    assert len(rendered.rendered_node_keys) == 3
    assert rendered.periodic_metadata["renderer_consumed_explicit_periodic_graph"]
    assert rendered.periodic_metadata["display_nodes"] == 3
