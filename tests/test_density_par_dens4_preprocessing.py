from __future__ import annotations

import numpy as np

from mdstats import (
    AtomisticFrameCollection,
    AtomicConnectivityGeometryCache,
    ConnectivityScope,
    DistanceConnectivity,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    HystereticDistanceConnectivity,
    PairCutoffRegistry,
    build_framework_topology,
    build_topology_catalog,
    compute_atomic_connectivity,
    prepare_framework_dynamics_scene,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey


def _trajectory(fractional: np.ndarray, atomic_numbers: np.ndarray) -> AtomisticFrameCollection:
    fractional = np.asarray(fractional, dtype=float)
    n_frames, n_atoms, _ = fractional.shape
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=np.repeat((np.eye(3) * 10.0)[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        provenance=FrameCollectionProvenance(
            source_format="par-dens4-synthetic",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_hysteretic_frame_parallel_geometry_matches_serial_fold_exactly() -> None:
    distances = np.asarray([1.0, 1.3, 1.7, 1.4, 1.1, 1.8, 1.0])
    frac = np.zeros((len(distances), 2, 3), dtype=float)
    frac[:, 0, :] = [0.10, 0.10, 0.10]
    frac[:, 1, :] = [0.20, 0.10, 0.10]
    frac[:, 1, 0] = 0.10 + distances / 10.0
    collection = _trajectory(frac, np.asarray([14, 8]))
    definition = HystereticDistanceConnectivity(
        formation_cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 1.2}),
        breaking_cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 1.6}),
        initial_state="formation_cutoff",
    )
    serial = compute_atomic_connectivity(collection, definition, parallel_frame_workers=1)
    parallel = compute_atomic_connectivity(collection, definition, parallel_frame_workers=4)
    np.testing.assert_array_equal(serial.frame_state_ids, parallel.frame_state_ids)
    assert [state.digest for state in serial.states] == [state.digest for state in parallel.states]
    assert [transition.to_dict() if hasattr(transition, "to_dict") else transition.transition_id for transition in serial.transitions] == [transition.to_dict() if hasattr(transition, "to_dict") else transition.transition_id for transition in parallel.transitions]
    diagnostics = parallel.metadata["neighbor_search"]
    assert diagnostics["par_dens4_frame_parallel_geometry"] is True
    assert diagnostics["par_dens4_parallel_workers"] == 4
    assert diagnostics["par_dens4_hysteresis_fold"] == "deterministic_collection_frame_order_v1"


def test_atomic_connectivity_geometry_cache_reuses_framework_pair_requests() -> None:
    base = np.asarray(
        [[0.10, 0.10, 0.10], [0.30, 0.10, 0.10], [0.20, 0.10, 0.10], [0.20, 0.20, 0.10]],
        dtype=float,
    )
    frac = np.repeat(base[None, :, :], 4, axis=0)
    collection = _trajectory(frac, np.asarray([14, 13, 8, 11]))
    shared = {("Si", "O"): 1.2, ("Al", "O"): 1.2}
    cache = AtomicConnectivityGeometryCache()
    framework = DistanceConnectivity(
        PairCutoffRegistry.from_mapping(shared),
        scope=ConnectivityScope.from_selection(included_species=("Si", "Al", "O")),
    )
    full = DistanceConnectivity(
        PairCutoffRegistry.from_mapping({**shared, ("Na", "O"): 1.2})
    )
    first = compute_atomic_connectivity(collection, framework, geometry_cache=cache)
    second = compute_atomic_connectivity(collection, full, geometry_cache=cache)
    first_cache = first.metadata["neighbor_search"]["geometry_cache"]
    second_cache = second.metadata["neighbor_search"]["geometry_cache"]
    assert first_cache["hits"] == 0
    assert second_cache["hits"] >= 2 * collection.n_frames
    assert second_cache["scientific_identity_includes_cache_state"] is False


def _partitioned_fixture():
    n_frames = 8
    atomic_numbers = np.asarray([14, 13, 8, 8], dtype=np.int32)
    base = np.asarray(
        [[0.10, 0.10, 0.10], [0.30, 0.10, 0.10], [0.20, 0.10, 0.10], [0.20, 0.20, 0.10]],
        dtype=float,
    )
    frac = np.repeat(base[None, :, :], n_frames, axis=0)
    frac[:, :, 2] += np.linspace(-0.004, 0.004, n_frames)[:, None]
    collection = _trajectory(frac, atomic_numbers)
    frame_edges = {
        frame: (
            (AtomicEdgeKey(0, 2), AtomicEdgeKey(2, 1))
            if frame < 4
            else (AtomicEdgeKey(0, 3), AtomicEdgeKey(3, 1))
        )
        for frame in range(n_frames)
    }
    connectivity = compute_atomic_connectivity(
        collection, ExplicitConnectivity(frame_edges=frame_edges)
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
    )
    return collection, build_topology_catalog(collection, connectivity, mapping)


def test_topology_categories_parallelize_and_reuse_frame_geometry() -> None:
    collection, catalog = _partitioned_fixture()
    serial = prepare_framework_dynamics_scene(
        collection,
        catalog,
        resources=FrameworkDynamicsResources(max_threads=1, max_memory_bytes="1GiB"),
    )
    parallel = prepare_framework_dynamics_scene(
        collection,
        catalog,
        resources=FrameworkDynamicsResources(max_threads=4, max_memory_bytes="1GiB"),
    )
    assert len(serial.topology_categories) == len(parallel.topology_categories) == 2
    assert serial.dominant_topology_id == parallel.dominant_topology_id
    for left, right in zip(serial.topology_categories, parallel.topology_categories, strict=True):
        assert left.topology_id == right.topology_id
        np.testing.assert_array_equal(left.mean_framework.node_positions_3d, right.mean_framework.node_positions_3d)
        np.testing.assert_array_equal(left.mean_framework.edge_image_shifts, right.mean_framework.edge_image_shifts)
    summary = parallel.metadata["topology_category_scheduler_summary"]
    assert summary["maximum_concurrent_tasks"] >= 2
    cache = parallel.metadata["framework_geometry_cache"]
    assert cache["policy"] == "par_dens4_frame_geometry_cache_v1"
    assert cache["hits"] > 0 or cache["bulk_static_projected_frames"] > 0
    assert parallel.metadata["topology_category_policy"] == "par_dens4_parallel_partitioned_category_graphs_v2"


def test_gfx3d_dominant_only_partitioned_fast_path_preserves_dominant_mean() -> None:
    collection, catalog = _partitioned_fixture()
    complete = prepare_framework_dynamics_scene(
        collection,
        catalog,
        resources=FrameworkDynamicsResources(max_threads=2, max_memory_bytes="1GiB"),
    )
    compact = prepare_framework_dynamics_scene(
        collection,
        catalog,
        resources=FrameworkDynamicsResources(max_threads=2, max_memory_bytes="1GiB"),
        _topology_category_mode="dominant_only",
    )
    assert compact.topology_categories == ()
    assert compact.topology_catalog is not None
    assert compact.dominant_topology_id == complete.dominant_topology_id
    np.testing.assert_array_equal(
        compact.mean_framework.node_positions_3d,
        complete.mean_framework.node_positions_3d,
    )
    np.testing.assert_array_equal(
        compact.mean_framework.edge_image_shifts,
        complete.mean_framework.edge_image_shifts,
    )
    assert compact.metadata["topology_category_policy"] == "gfx3d_dominant_only_fast_path_v1"
    assert compact.metadata["topology_category_materialization_omitted"] is True
