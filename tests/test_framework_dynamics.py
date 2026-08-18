"""Plot-D1/D2 registered mean-framework and trajectory overlay tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    CallbackProgressPort,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    AtomicMeanGraph3DRenderOptions,
    AtomicMeanGraphOptions,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    Graph3DRenderOptions,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    SpatialRegistrationMode,
    TrajectoryAtomSelection,
    TrajectoryDisplayMode,
    build_framework_topology,
    compute_atomic_connectivity,
    plot_framework_dynamics_3d,
    prepare_framework_dynamics_scene,
)
from mdstats.exceptions import TrajectoryRequiredError
from mdstats.plotting import GraphComplexityError


def make_collection(
    fractional: np.ndarray,
    *,
    cells: np.ndarray | None = None,
    semantics: FrameSemantics = FrameSemantics.TRAJECTORY,
) -> AtomisticFrameCollection:
    frac = np.asarray(fractional, dtype=float)
    n_frames, n_atoms, _ = frac.shape
    if cells is None:
        cells = np.repeat((np.eye(3) * 10.0)[None, :, :], n_frames, axis=0)
    cells = np.asarray(cells, dtype=float)
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(100, 100 + n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11][:n_atoms], dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=(
            np.arange(n_frames, dtype=np.int64)
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        times=(
            np.arange(n_frames, dtype=float) * 2.0
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=frac,
        velocities=(
            np.zeros((n_frames, n_atoms, 3), dtype=float)
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-framework-dynamics",
            source_files=("synthetic",),
            velocity_source=(
                "synthetic" if semantics is FrameSemantics.TRAJECTORY else "unavailable"
            ),
            coordinate_normalization=(
                "time_unwrapped_fractional"
                if semantics is FrameSemantics.TRAJECTORY
                else "independent_frame_wrapping"
            ),
            stress_source=None,
            units_source="synthetic",
        ),
    )


def mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols(
                "T-O-T", ("O",), edge_kind="oxygen_bridge"
            ),
        ),
    )


def topology_for(collection: AtomisticFrameCollection):
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.1, ("Al", "O"): 2.1}
        )
    )
    state = compute_atomic_connectivity(collection, definition).states[0]
    return build_framework_topology(state, mapping())


def base_fractional(n_frames: int = 3) -> np.ndarray:
    one = np.asarray(
        [
            [0.10, 0.10, 0.10],
            [0.20, 0.10, 0.10],
            [0.30, 0.10, 0.10],
            [0.80, 0.50, 0.50],
        ]
    )
    return np.repeat(one[None, :, :], n_frames, axis=0)




def test_prepare_scene_emits_structured_progress_events() -> None:
    collection = make_collection(base_fractional(n_frames=4))
    topology = topology_for(collection)
    events = []
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(species=("Na",)),
        progress=CallbackProgressPort(events.append),
    )
    assert scene.trajectory_paths is not None
    assert events[0].source == "plotting.framework_dynamics.prepare"
    assert events[0].stage == "scene_preparation"
    registration = [
        event for event in events if event.stage == "framework_registration"
    ]
    assert registration[0].current == 0
    assert registration[-1].current == registration[-1].total == 4
    assert events[-1].status == "completed"
    assert events[-1].stage == "scene_preparation"


def test_prepare_scene_legacy_progress_callback_remains_available() -> None:
    collection = make_collection(base_fractional(n_frames=2))
    topology = topology_for(collection)
    messages: list[str] = []
    with pytest.warns(DeprecationWarning):
        prepare_framework_dynamics_scene(
            collection,
            topology,
            progress_callback=messages.append,
        )
    assert messages[0].startswith("scene_preparation:")
    assert messages[-1].startswith("scene_preparation:")


def test_species_and_explicit_selection_resolve_as_union() -> None:
    collection = make_collection(base_fractional())
    topology = topology_for(collection)
    selection = TrajectoryAtomSelection(atom_indices=(0,), species=("Na",), label="T+Na")
    scene = prepare_framework_dynamics_scene(
        collection, topology, trajectory_selection=selection
    )
    assert scene.trajectory_paths is not None
    assert scene.trajectory_paths.atom_indices == (0, 3)
    assert scene.trajectory_paths.selection_label == "T+Na"


def test_trajectory_overlay_rejects_independent_ensemble() -> None:
    ensemble = make_collection(
        base_fractional(), semantics=FrameSemantics.ENSEMBLE
    )
    topology = topology_for(ensemble)
    with pytest.raises(TrajectoryRequiredError):
        prepare_framework_dynamics_scene(
            ensemble,
            topology,
            trajectory_selection=TrajectoryAtomSelection(species=("Na",)),
        )
    mean_only = prepare_framework_dynamics_scene(ensemble, topology)
    assert mean_only.trajectory_paths is None


def test_continuous_path_preserves_periodic_crossing() -> None:
    frac = base_fractional()
    frac[:, 3, 0] = [0.90, 1.05, 1.20]
    collection = make_collection(frac)
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(atom_indices=(3,)),
    )
    assert scene.trajectory_paths is not None
    path = scene.trajectory_paths
    np.testing.assert_allclose(path.continuous_positions[0, :, 0], [9.0, 10.5, 12.0])
    assert not np.any(path.segment_breaks)


def test_folded_path_inserts_boundary_breaks() -> None:
    frac = base_fractional()
    frac[:, 3, 0] = [0.90, 1.05, 1.20]
    collection = make_collection(frac)
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(atom_indices=(3,)),
        options=FrameworkDynamicsOptions(
            trajectory_display_mode=TrajectoryDisplayMode.FOLDED
        ),
    )
    assert scene.trajectory_paths is not None
    path = scene.trajectory_paths
    np.testing.assert_allclose(path.display_positions[0, :, 0], [9.0, 0.5, 2.0])
    np.testing.assert_array_equal(path.segment_breaks, [[True, False]])


def test_material_registration_removes_homogeneous_cell_scaling() -> None:
    frac = base_fractional(2)
    cells = np.asarray([np.eye(3) * 10.0, np.eye(3) * 12.0])
    collection = make_collection(frac, cells=cells)
    topology = topology_for(collection)
    material = prepare_framework_dynamics_scene(collection, topology)
    laboratory = prepare_framework_dynamics_scene(
        collection,
        topology,
        options=FrameworkDynamicsOptions(
            registration_mode=SpatialRegistrationMode.LABORATORY,
            display_cell="reference",
        ),
    )
    np.testing.assert_allclose(
        material.mean_framework.node_positions_3d[:, 0], [1.0, 3.0]
    )
    np.testing.assert_allclose(
        laboratory.mean_framework.node_positions_3d[:, 0], [1.1, 3.3]
    )


def test_variable_cell_laboratory_trajectory_remains_supported() -> None:
    frac = base_fractional(2)
    cells = np.asarray([np.eye(3) * 10.0, np.eye(3) * 12.0])
    collection = make_collection(frac, cells=cells)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology_for(collection),
        trajectory_selection=TrajectoryAtomSelection(atom_indices=(3,)),
        options=FrameworkDynamicsOptions(
            registration_mode=SpatialRegistrationMode.LABORATORY,
            display_cell="reference",
        ),
    )
    assert scene.trajectory_paths is not None
    np.testing.assert_allclose(
        scene.trajectory_paths.continuous_positions[0, :, 0], [8.0, 9.6]
    )
    assert scene.metadata["cell_equivalent"] is False


def test_framework_registered_mode_removes_rigid_drift_from_graph_and_path() -> None:
    frac = base_fractional(3)
    drift = np.asarray([0.0, 0.15, 0.30])
    frac[:, :, 0] += drift[:, None]
    collection = make_collection(frac)
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(atom_indices=(3,)),
        options=FrameworkDynamicsOptions(
            registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED
        ),
    )
    np.testing.assert_allclose(
        scene.mean_framework.node_positions_3d[:, 0], [1.0, 3.0], atol=1.0e-12
    )
    assert scene.trajectory_paths is not None
    np.testing.assert_allclose(
        scene.trajectory_paths.continuous_positions[0, :, 0], [8.0, 8.0, 8.0]
    )


def test_reference_and_mean_display_cells_are_explicit() -> None:
    frac = base_fractional(2)
    cells = np.asarray([np.eye(3) * 10.0, np.eye(3) * 14.0])
    collection = make_collection(frac, cells=cells)
    topology = topology_for(collection)
    reference = prepare_framework_dynamics_scene(collection, topology)
    mean = prepare_framework_dynamics_scene(
        collection, topology, options=FrameworkDynamicsOptions(display_cell="mean")
    )
    np.testing.assert_allclose(reference.display_cell, np.eye(3) * 10.0)
    np.testing.assert_allclose(mean.display_cell, np.eye(3) * 12.0)
    np.testing.assert_allclose(mean.mean_framework.node_positions_3d[:, 0], [1.2, 3.6])


def test_resource_preflight_occurs_before_scene_construction() -> None:
    collection = make_collection(base_fractional(3))
    topology = topology_for(collection)
    with pytest.raises(GraphComplexityError, match="max_frames"):
        prepare_framework_dynamics_scene(
            collection,
            topology,
            resources=FrameworkDynamicsResources(max_frames=2),
        )
    with pytest.raises(GraphComplexityError, match="max_trajectory_atoms"):
        prepare_framework_dynamics_scene(
            collection,
            topology,
            trajectory_selection=TrajectoryAtomSelection(atom_indices=(0, 3)),
            resources=FrameworkDynamicsResources(max_trajectory_atoms=1),
        )
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(atom_indices=(3,)),
    )
    with pytest.raises(GraphComplexityError, match="max_plotly_traces"):
        plot_framework_dynamics_3d(
            scene, graph_options=Graph3DRenderOptions(max_plotly_traces=1)
        )


def test_mean_framework_preserves_scientific_graph_identity_and_winding() -> None:
    frac = base_fractional(2)
    frac[:, 0, 0] = 0.92
    frac[:, 1, 0] = 0.00
    frac[:, 2, 0] = 0.08
    collection = make_collection(frac)
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(collection, topology)
    assert scene.mean_framework.node_keys == tuple(topology.vertex_atom_indices.tolist())
    assert scene.mean_framework.edge_keys == topology.edge_keys
    vector = (
        scene.mean_framework.node_positions_3d[1]
        + scene.mean_framework.edge_image_shifts[0] @ scene.display_cell
        - scene.mean_framework.node_positions_3d[0]
    )
    assert np.linalg.norm(vector) == pytest.approx(1.6)



def test_mean_framework_is_canonical_and_boundary_edges_remain_short() -> None:
    frac = base_fractional(2)
    frac[:, 0, 0] = 0.92
    frac[:, 1, 0] = 0.00
    frac[:, 2, 0] = 0.08
    collection = make_collection(frac)
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(collection, topology)
    inverse = np.linalg.inv(scene.display_cell)
    mean_fractional = scene.mean_framework.node_positions_3d @ inverse
    assert np.all(mean_fractional >= -1.0e-12)
    assert np.all(mean_fractional < 1.0 + 1.0e-12)
    endpoints = scene.mean_framework.edge_endpoints
    vectors = (
        scene.mean_framework.node_positions_3d[endpoints[:, 1]]
        + scene.mean_framework.edge_image_shifts @ scene.display_cell
        - scene.mean_framework.node_positions_3d[endpoints[:, 0]]
    )
    assert float(np.max(np.linalg.norm(vectors, axis=1))) < 3.0


def test_composite_legend_groups_paths_and_recomputes_equal_aspect() -> None:
    collection = make_collection(base_fractional())
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(atom_indices=(0, 3), label="mobile"),
    )
    result = plot_framework_dynamics_3d(scene)
    unique_path_ids = sorted(
        {indexes[0] for indexes in result.trajectory_trace_indices.values()}
    )
    path_traces = [result.figure.data[index] for index in unique_path_ids]
    assert {trace.legendgroup for trace in path_traces} == {
        "trajectory-species:Na",
        "trajectory-species:Si",
    }
    assert sum(bool(trace.showlegend) for trace in path_traces) == 2
    assert result.figure.layout.legend.groupclick == "togglegroup"
    assert result.figure.layout.scene.aspectmode == "manual"
    ranges = [
        result.figure.layout.scene.xaxis.range,
        result.figure.layout.scene.yaxis.range,
        result.figure.layout.scene.zaxis.range,
    ]
    extents = np.asarray([float(high - low) for low, high in ranges])
    ratio = result.figure.layout.scene.aspectratio
    rendered = np.asarray([ratio.x, ratio.y, ratio.z], dtype=float)
    np.testing.assert_allclose(rendered, extents / np.max(extents), atol=1.0e-12)

def test_plotly_composite_adds_paths_endpoints_and_serializes(tmp_path) -> None:
    collection = make_collection(base_fractional())
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        trajectory_selection=TrajectoryAtomSelection(species=("Na",)),
    )
    result = plot_framework_dynamics_3d(scene)
    assert set(result.trajectory_trace_indices) == {3}
    assert len(result.endpoint_trace_indices) == 2
    endpoint_traces = [result.figure.data[index] for index in result.endpoint_trace_indices]
    assert [trace.name for trace in endpoint_traces] == [
        "selected atoms start",
        "selected atoms end",
    ]
    assert [trace.legendgroup for trace in endpoint_traces] == [
        "trajectory-endpoint:start",
        "trajectory-endpoint:end",
    ]
    assert all(bool(trace.showlegend) for trace in endpoint_traces)
    assert [trace.marker.symbol for trace in endpoint_traces] == ["circle", "diamond"]
    target = tmp_path / "framework-dynamics.html"
    result.write_html(target)
    assert target.stat().st_size > 10_000


def atomic_connectivity_for(collection: AtomisticFrameCollection):
    definition = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.1, ("Al", "O"): 2.1, ("O", "Na"): 1.5}
        )
    )
    return compute_atomic_connectivity(collection, definition)


def test_atomic_mean_graph_occupancy_threshold_filters_transient_edges() -> None:
    frac = base_fractional(3)
    frac[:, 3, :] = np.asarray(
        [
            [0.70, 0.50, 0.50],
            [0.31, 0.10, 0.10],
            [0.70, 0.50, 0.50],
        ]
    )
    collection = make_collection(frac)
    topology = topology_for(collection)
    connectivity = atomic_connectivity_for(collection)

    strict = prepare_framework_dynamics_scene(
        collection,
        topology,
        atomic_connectivity=connectivity,
        atomic_mean_graph_options=AtomicMeanGraphOptions(
            mode="occupancy", occupancy_threshold=0.5
        ),
    )
    assert strict.atomic_mean_graph is not None
    strict_edges = {
        tuple(strict.atomic_mean_graph.atom_indices[index] for index in endpoint)
        for endpoint in strict.atomic_mean_graph.edge_endpoints
    }
    assert (1, 3) not in strict_edges

    permissive = prepare_framework_dynamics_scene(
        collection,
        topology,
        atomic_connectivity=connectivity,
        atomic_mean_graph_options=AtomicMeanGraphOptions(
            mode="occupancy", occupancy_threshold=0.2
        ),
    )
    assert permissive.atomic_mean_graph is not None
    permissive_pairs = [
        tuple(permissive.atomic_mean_graph.atom_indices[index] for index in endpoint)
        for endpoint in permissive.atomic_mean_graph.edge_endpoints
    ]
    assert (1, 3) in permissive_pairs
    transient_index = permissive_pairs.index((1, 3))
    assert permissive.atomic_mean_graph.edge_occupancies[transient_index] == pytest.approx(1.0 / 3.0)


def test_atomic_mean_graph_accepts_uniform_state_input() -> None:
    collection = make_collection(base_fractional())
    topology = topology_for(collection)
    connectivity = atomic_connectivity_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        atomic_connectivity=connectivity.states[0],
        atomic_mean_graph_options=AtomicMeanGraphOptions(mode="persistent"),
    )
    assert scene.atomic_mean_graph is not None
    assert np.allclose(scene.atomic_mean_graph.edge_occupancies, 1.0)


def test_composite_render_adds_atomic_mean_graph_species_traces() -> None:
    frac = base_fractional(3)
    frac[:, 3, :] = np.asarray(
        [
            [0.70, 0.50, 0.50],
            [0.31, 0.10, 0.10],
            [0.70, 0.50, 0.50],
        ]
    )
    collection = make_collection(frac)
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        atomic_connectivity=atomic_connectivity_for(collection),
        atomic_mean_graph_options=AtomicMeanGraphOptions(
            mode="occupancy", occupancy_threshold=0.2
        ),
    )
    result = plot_framework_dynamics_3d(
        scene, atomic_mean_graph_options=AtomicMeanGraph3DRenderOptions()
    )
    assert {"Si", "Al", "O", "Na", "bonds"}.issubset(
        set(result.atomic_mean_graph_trace_indices)
    )
    names = {trace.name for trace in result.figure.data}
    assert "Atomic bonds" in names
    assert "Na atoms" in names
    assert result.figure.layout.legend.groupclick == "togglegroup"


def test_atomic_mean_vertices_ignore_connectivity_gauge_changes() -> None:
    fractional = np.asarray(
        [
            [
                [0.10, 0.10, 0.10],
                [0.40, 0.10, 0.10],
                [0.80, 0.10, 0.10],
            ],
            [
                [0.15, 0.10, 0.10],
                [0.40, 0.10, 0.10],
                [0.80, 0.10, 0.10],
            ],
        ],
        dtype=float,
    )
    cells = np.repeat(np.eye(3)[None, :, :], 2, axis=0)
    collection = make_collection(fractional, cells=cells)
    connectivity = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {
                    ("Si", "O"): 0.35,
                    ("O", "Al"): 0.45,
                    ("Si", "Al"): 0.32,
                }
            )
        ),
    )
    assert connectivity.n_states == 2
    assert connectivity.states[0].n_edges == 3
    assert connectivity.states[1].n_edges == 2

    scene = prepare_framework_dynamics_scene(
        collection,
        build_framework_topology(connectivity.states[0], mapping()),
        atomic_connectivity=connectivity,
        atomic_mean_graph_options=AtomicMeanGraphOptions(
            mode="occupancy", occupancy_threshold=0.4
        ),
    )
    assert scene.atomic_mean_graph is not None
    mean_fractional = (
        scene.atomic_mean_graph.display_positions @ np.linalg.inv(scene.display_cell)
    )
    np.testing.assert_allclose(
        mean_fractional,
        np.asarray(
            [
                [0.125, 0.10, 0.10],
                [0.400, 0.10, 0.10],
                [0.800, 0.10, 0.10],
            ]
        ),
        rtol=0.0,
        atol=1.0e-12,
    )
    endpoints = scene.atomic_mean_graph.edge_endpoints
    vectors = (
        scene.atomic_mean_graph.display_positions[endpoints[:, 1]]
        + scene.atomic_mean_graph.edge_image_shifts @ scene.display_cell
        - scene.atomic_mean_graph.display_positions[endpoints[:, 0]]
    )
    assert float(np.max(np.linalg.norm(vectors, axis=1))) <= 0.4 + 1.0e-12
