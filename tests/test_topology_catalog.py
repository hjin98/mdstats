"""Stage 3 tests for exact multi-frame framework topology catalogs."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

import mdstats.analysis.topology_catalog as topology_catalog_module
from mdstats import (
    AtomisticFrameCollection,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkMapping,
    FrameworkPathRule,
    TopologyCatalog,
    TopologyCatalogInputError,
    TopologyCatalogOptions,
    TopologyConsistency,
    TopologySegmentStatus,
    build_topology_catalog,
    compute_atomic_connectivity,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey


def make_collection(
    atomic_numbers: list[int],
    n_frames: int,
    *,
    semantics: FrameSemantics,
) -> AtomisticFrameCollection:
    n_atoms = len(atomic_numbers)
    cell = np.eye(3) * 12.0
    fractional = np.zeros((n_frames, n_atoms, 3), dtype=float)
    fractional[:, :, 0] = np.linspace(0.05, 0.85, n_atoms)
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(100, 100 + n_frames, dtype=np.int64),
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
        cells=np.repeat(cell[None, ...], n_frames, axis=0),
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
            coordinate_normalization=(
                "minimum_image_inferred"
                if semantics is FrameSemantics.TRAJECTORY
                else "independent_frame_wrapping"
            ),
            stress_source=None,
            units_source="synthetic",
        ),
    )


def tot_mapping(*, include_na: bool = False) -> FrameworkMapping:
    roles = {"Si": "vertex", "Al": "vertex", "O": "linker"}
    if include_na:
        roles["Na"] = "spectator"
    return FrameworkMapping.from_symbol_roles(
        roles,
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
        name="T-O-T",
    )


def trajectory_catalog(sequence: str = "AABBA", *, minimum_persistent_frames: int = 1):
    collection = make_collection(
        [14, 8, 13], len(sequence), semantics=FrameSemantics.TRAJECTORY
    )
    edge_frames = {
        frame: ((AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)) if label == "A" else ())
        for frame, label in enumerate(sequence)
    }
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(frame_edges=edge_frames),
    )
    catalog = build_topology_catalog(
        collection,
        connectivity,
        tot_mapping(),
        catalog_options=TopologyCatalogOptions(
            minimum_persistent_frames=minimum_persistent_frames
        ),
    )
    return collection, connectivity, catalog


def test_uniform_catalog_compresses_connectivity_states_that_do_not_change_framework() -> (
    None
):
    collection = make_collection([14, 8, 13, 11], 2, semantics=FrameSemantics.ENSEMBLE)
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            frame_edges={
                0: (
                    AtomicEdgeKey(0, 1),
                    AtomicEdgeKey(1, 2),
                    AtomicEdgeKey(1, 3),
                ),
                1: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
            }
        ),
    )
    catalog = build_topology_catalog(
        collection, connectivity, tot_mapping(include_na=True)
    )
    assert connectivity.n_states == 2
    assert catalog.consistency is TopologyConsistency.UNIFORM
    assert catalog.n_topologies == 1
    np.testing.assert_array_equal(catalog.frame_topology_ids, [0, 0])
    np.testing.assert_array_equal(catalog.connectivity_state_topology_ids, [0, 0])
    assert catalog.segments is None
    assert catalog.transitions == ()


def test_partitioned_trajectory_has_classes_segments_and_recurring_identity() -> None:
    _, _, catalog = trajectory_catalog("AABBA")
    assert catalog.consistency is TopologyConsistency.PARTITIONED
    assert catalog.n_topologies == 2
    np.testing.assert_array_equal(catalog.frame_topology_ids, [0, 0, 1, 1, 0])
    assert catalog.segments is not None
    assert [segment.topology_id for segment in catalog.segments] == [0, 1, 0]
    assert [
        (s.result_position_start, s.result_position_stop) for s in catalog.segments
    ] == [
        (0, 2),
        (2, 4),
        (4, 5),
    ]
    assert len(catalog.transitions) == 2
    assert catalog.transitions[0].removed_framework_edges
    assert catalog.transitions[1].added_framework_edges


def test_segment_persistence_is_descriptive_only() -> None:
    _, _, catalog = trajectory_catalog("AABBA", minimum_persistent_frames=2)
    assert catalog.segments is not None
    assert [segment.status for segment in catalog.segments] == [
        TopologySegmentStatus.CONFIRMED,
        TopologySegmentStatus.CONFIRMED,
        TopologySegmentStatus.TRANSIENT,
    ]
    np.testing.assert_array_equal(catalog.frame_topology_ids, [0, 0, 1, 1, 0])
    assert len(catalog.transitions) == 2


def test_ensemble_has_frame_groups_but_no_temporal_records() -> None:
    collection = make_collection([14, 8, 13], 3, semantics=FrameSemantics.ENSEMBLE)
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            frame_edges={
                0: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
                1: (),
                2: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
            }
        ),
    )
    catalog = build_topology_catalog(collection, connectivity, tot_mapping())
    np.testing.assert_array_equal(catalog.frame_topology_ids, [0, 1, 0])
    np.testing.assert_array_equal(catalog.frame_groups[0].result_positions, [0, 2])
    np.testing.assert_array_equal(catalog.frame_groups[1].result_positions, [1])
    assert catalog.segments is None
    assert catalog.transitions == ()


def test_per_frame_mode_exposes_one_public_topology_per_frame() -> None:
    collection, connectivity, _ = trajectory_catalog("AAA")
    catalog = build_topology_catalog(
        collection,
        connectivity,
        tot_mapping(),
        catalog_options=TopologyCatalogOptions(mode="per_frame"),
    )
    assert catalog.consistency is TopologyConsistency.PER_FRAME
    assert catalog.n_topologies == 3
    np.testing.assert_array_equal(catalog.frame_topology_ids, [0, 1, 2])
    assert catalog.connectivity_state_topology_ids.size == 0
    assert catalog.segments is None
    assert catalog.transitions == ()


def test_transition_difference_storage_can_be_disabled_without_losing_affected_sets() -> (
    None
):
    collection, connectivity, _ = trajectory_catalog("AB")
    catalog = build_topology_catalog(
        collection,
        connectivity,
        tot_mapping(),
        catalog_options=TopologyCatalogOptions(
            include_atomic_edge_differences=False,
            include_framework_edge_differences=False,
        ),
    )
    transition = catalog.transitions[0]
    assert transition.added_atomic_edges == ()
    assert transition.removed_atomic_edges == ()
    assert transition.added_framework_edges == ()
    assert transition.removed_framework_edges == ()
    assert transition.affected_atom_indices == (0, 1, 2)
    assert transition.affected_vertex_atom_indices == (0, 2)
    assert transition.affected_linker_atom_indices == (1,)


def test_asymmetric_linker_order_produces_distinct_topology_classes() -> None:
    collection = make_collection(
        [14, 8, 16, 16, 8, 13], 2, semantics=FrameSemantics.TRAJECTORY
    )
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            frame_edges={
                0: (
                    AtomicEdgeKey(0, 1),
                    AtomicEdgeKey(1, 2),
                    AtomicEdgeKey(2, 5),
                ),
                1: (
                    AtomicEdgeKey(0, 3),
                    AtomicEdgeKey(3, 4),
                    AtomicEdgeKey(4, 5),
                ),
            }
        ),
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker", "S": "linker"},
        path_rules=(
            FrameworkPathRule.from_symbols(
                "Si-O-S-Al", ("O", "S"), endpoint_symbols=("Si", "Al")
            ),
            FrameworkPathRule.from_symbols(
                "Si-S-O-Al", ("S", "O"), endpoint_symbols=("Si", "Al")
            ),
        ),
    )
    catalog = build_topology_catalog(collection, connectivity, mapping)
    assert catalog.n_topologies == 2
    first, second = catalog.topologies
    assert first.edge_keys[0].rule_id == "Si-O-S-Al"
    assert second.edge_keys[0].rule_id == "Si-S-O-Al"
    assert catalog.transitions[0].added_framework_edges
    assert catalog.transitions[0].removed_framework_edges


def test_serialization_round_trip_and_digest_verification() -> None:
    _, _, catalog = trajectory_catalog("AABBA", minimum_persistent_frames=2)
    restored = TopologyCatalog.from_dict(catalog.to_dict())
    assert restored == catalog
    assert restored.digest == catalog.digest
    payload = catalog.to_dict()
    payload["frame_topology_ids"][0] = 1
    with pytest.raises(Exception, match="inconsistent|disagree|duplicate"):
        TopologyCatalog.from_dict(payload)


def test_convenience_queries_are_explicit_about_frames_and_positions() -> None:
    _, _, catalog = trajectory_catalog("AABBA")
    assert catalog.topology_id_for_frame(100 - 100) == 0
    # Collection frame indices are 0..4; frame IDs are 100..104.
    np.testing.assert_array_equal(catalog.frames_for_topology(0), [0, 1, 4])
    np.testing.assert_array_equal(catalog.result_positions_for_topology(0), [0, 1, 4])
    assert catalog.topology_for_frame(2) is catalog.topologies[1]
    differences = catalog.compare_topologies(0, 1)
    assert differences["removed_edges"]
    assert catalog.to_networkx(0).number_of_nodes() == 2


def test_catalog_arrays_are_read_only() -> None:
    _, _, catalog = trajectory_catalog("AB")
    with pytest.raises(ValueError):
        catalog.frame_topology_ids[0] = 7
    with pytest.raises(ValueError):
        catalog.frame_groups[0].result_positions[0] = 7
    with pytest.raises(ValueError):
        catalog.topology_counts[0] = 7


def test_projection_occurs_once_per_source_connectivity_state(monkeypatch) -> None:
    collection, connectivity, _ = trajectory_catalog("AABBA")
    original = topology_catalog_module.build_framework_topology
    calls: list[str] = []

    def counted(state, mapping, **kwargs):
        calls.append(state.digest)
        return original(state, mapping, **kwargs)

    monkeypatch.setattr(topology_catalog_module, "build_framework_topology", counted)
    build_topology_catalog(collection, connectivity, tot_mapping())
    assert len(calls) == connectivity.n_states
    assert len(set(calls)) == connectivity.n_states


def test_collection_frame_id_mismatch_is_rejected() -> None:
    collection, connectivity, _ = trajectory_catalog("AB")
    bad = replace(connectivity, frame_ids=np.asarray([999, 1000], dtype=np.int64))
    with pytest.raises(TopologyCatalogInputError, match="frame IDs"):
        build_topology_catalog(collection, bad, tot_mapping())


def test_ensemble_reordering_preserves_structural_class_set() -> None:
    collection = make_collection([14, 8, 13], 3, semantics=FrameSemantics.ENSEMBLE)
    definition = ExplicitConnectivity(
        frame_edges={
            0: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
            1: (),
            2: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
        }
    )
    ordered = compute_atomic_connectivity(
        collection, definition, frame_indices=[0, 1, 2]
    )
    permuted = compute_atomic_connectivity(
        collection, definition, frame_indices=[1, 0, 2]
    )
    first = build_topology_catalog(collection, ordered, tot_mapping())
    second = build_topology_catalog(collection, permuted, tot_mapping())
    assert {topology.digest for topology in first.topologies} == {
        topology.digest for topology in second.topologies
    }
    assert sorted(first.topology_counts.tolist()) == sorted(
        second.topology_counts.tolist()
    )
    assert first.transitions == second.transitions == ()


def test_options_are_part_of_catalog_identity_but_not_frame_assignment() -> None:
    collection, connectivity, first = trajectory_catalog("AABBA")
    second = build_topology_catalog(
        collection,
        connectivity,
        tot_mapping(),
        catalog_options=TopologyCatalogOptions(minimum_persistent_frames=3),
    )
    np.testing.assert_array_equal(first.frame_topology_ids, second.frame_topology_ids)
    assert first.digest != second.digest


def test_invalid_catalog_options_are_rejected() -> None:
    with pytest.raises(Exception, match="positive integer"):
        TopologyCatalogOptions(minimum_persistent_frames=0)
    with pytest.raises(Exception, match="must be a bool"):
        TopologyCatalogOptions(include_atomic_edge_differences=1)  # type: ignore[arg-type]
    with pytest.raises(Exception, match="catalog.*per_frame"):
        TopologyCatalogOptions(mode="other")  # type: ignore[arg-type]


def test_duplicate_and_nonmonotonic_trajectory_frames_are_rejected() -> None:
    collection, connectivity, _ = trajectory_catalog("AB")
    duplicate = replace(
        connectivity,
        frame_indices=np.asarray([0, 0], dtype=np.int64),
        frame_ids=np.asarray([100, 100], dtype=np.int64),
    )
    with pytest.raises(TopologyCatalogInputError, match="unique"):
        build_topology_catalog(collection, duplicate, tot_mapping())

    nonmonotonic = replace(
        connectivity,
        frame_indices=np.asarray([1, 0], dtype=np.int64),
        frame_ids=np.asarray([101, 100], dtype=np.int64),
    )
    with pytest.raises(TopologyCatalogInputError, match="strictly increasing"):
        build_topology_catalog(collection, nonmonotonic, tot_mapping())


def test_projection_error_reports_state_id_and_digest() -> None:
    collection, connectivity, _ = trajectory_catalog("A")
    bad_mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex"},
        path_rules=(),
    )
    state_digest = connectivity.states[0].digest
    with pytest.raises(Exception) as exc_info:
        build_topology_catalog(collection, connectivity, bad_mapping)
    message = str(exc_info.value)
    assert "state 0" in message
    assert state_digest in message


def test_uniform_trajectory_has_one_confirmed_segment_and_no_transition() -> None:
    _, _, catalog = trajectory_catalog("AAAA", minimum_persistent_frames=3)
    assert catalog.is_uniform
    assert catalog.segments is not None
    assert len(catalog.segments) == 1
    assert catalog.segments[0].status is TopologySegmentStatus.CONFIRMED
    assert catalog.transitions == ()


def test_trajectory_atomic_state_changes_without_framework_change_have_no_transition() -> (
    None
):
    collection = make_collection(
        [14, 8, 13, 11], 3, semantics=FrameSemantics.TRAJECTORY
    )
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            frame_edges={
                0: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
                1: (
                    AtomicEdgeKey(0, 1),
                    AtomicEdgeKey(1, 2),
                    AtomicEdgeKey(1, 3),
                ),
                2: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
            }
        ),
    )
    catalog = build_topology_catalog(
        collection, connectivity, tot_mapping(include_na=True)
    )
    assert connectivity.n_states == 2
    assert catalog.n_topologies == 1
    assert catalog.segments is not None and len(catalog.segments) == 1
    assert catalog.transitions == ()


def test_sparse_trajectory_transition_preserves_selected_frame_indices() -> None:
    collection = make_collection([14, 8, 13], 3, semantics=FrameSemantics.TRAJECTORY)
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            frame_edges={
                0: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
                1: (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
                2: (),
            }
        ),
        frame_indices=[0, 2],
    )
    catalog = build_topology_catalog(collection, connectivity, tot_mapping())
    transition = catalog.transitions[0]
    assert transition.result_position_before == 0
    assert transition.result_position_after == 1
    assert transition.collection_frame_index_before == 0
    assert transition.collection_frame_index_after == 2
    assert transition.frame_id_before == 100
    assert transition.frame_id_after == 102


def test_variable_cells_do_not_split_a_connectivity_preserving_catalog() -> None:
    collection = make_collection([14, 8, 13], 3, semantics=FrameSemantics.TRAJECTORY)
    collection.cells[1] = np.diag([13.0, 12.0, 11.0])
    collection.cells[2] = np.asarray(
        [[12.0, 0.0, 0.0], [1.5, 11.5, 0.0], [0.5, 0.8, 12.5]]
    )
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(uniform_edges=(AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2))),
    )
    catalog = build_topology_catalog(collection, connectivity, tot_mapping())
    assert catalog.consistency is TopologyConsistency.UNIFORM
    assert catalog.n_topologies == 1


def _repeat_collection(
    collection: AtomisticFrameCollection, n_frames: int
) -> AtomisticFrameCollection:
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=collection.atomic_numbers,
        masses=collection.masses,
        pbc=collection.pbc,
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=np.repeat(collection.cells[:1], n_frames, axis=0),
        origins=np.repeat(collection.origins[:1], n_frames, axis=0),
        fractional_positions=np.repeat(
            collection.fractional_positions[:1], n_frames, axis=0
        ),
        velocities=np.zeros((n_frames, collection.n_atoms, 3)),
        provenance=replace(
            collection.provenance,
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
        ),
    )


def test_relaxed_na_lta_broad_spectator_contacts_reconcile_to_one_topology() -> None:
    from pathlib import Path

    from mdstats import (
        ConnectivityScope,
        DistanceConnectivity,
        FrameworkAtomRole,
        PairCutoffRegistry,
        read_structure,
    )

    structure = Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR"
    single = read_structure(structure, format="vasp")
    strict = compute_atomic_connectivity(
        single,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.0, ("Al", "O"): 2.0}
            ),
            scope=ConnectivityScope.from_selection(
                included_atom_indices=tuple(range(144))
            ),
        ),
    ).states[0]
    broad = compute_atomic_connectivity(
        single,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {
                    ("Si", "O"): 2.0,
                    ("Al", "O"): 2.0,
                    ("Na", "O"): 3.15,
                }
            )
        ),
    ).states[0]
    collection = _repeat_collection(single, 2)
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(frame_edges={0: strict.edge_keys, 1: broad.edge_keys}),
    )
    mapping = tot_mapping(include_na=True)
    assert mapping.species_roles[11] is FrameworkAtomRole.SPECTATOR
    catalog = build_topology_catalog(collection, connectivity, mapping)
    assert connectivity.n_states == 2
    assert catalog.n_topologies == 1
    assert catalog.topologies[0].n_vertices == 48
    assert catalog.topologies[0].n_edges == 96
    assert catalog.transitions == ()


def test_relaxed_na_lta_controlled_framework_edge_removal_partitions_catalog() -> None:
    from pathlib import Path

    from mdstats import (
        ConnectivityScope,
        DistanceConnectivity,
        PairCutoffRegistry,
        read_structure,
    )

    structure = Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR"
    single = read_structure(structure, format="vasp")
    state = compute_atomic_connectivity(
        single,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.0, ("Al", "O"): 2.0}
            ),
            scope=ConnectivityScope.from_selection(
                included_atom_indices=tuple(range(144))
            ),
        ),
    ).states[0]
    damaged_edges = state.edge_keys[1:]
    collection = _repeat_collection(single, 2)
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            scope=ConnectivityScope.from_selection(
                included_atom_indices=tuple(range(144))
            ),
            frame_edges={0: state.edge_keys, 1: damaged_edges},
        ),
    )
    catalog = build_topology_catalog(collection, connectivity, tot_mapping())
    assert catalog.n_topologies == 2
    assert catalog.topologies[0].n_edges == 96
    assert catalog.topologies[1].n_edges < 96
    assert len(catalog.transitions) == 1
    assert catalog.transitions[0].removed_atomic_edges
    assert catalog.transitions[0].removed_framework_edges


def test_digest_bucket_collision_cannot_merge_unequal_structural_keys(
    monkeypatch,
) -> None:
    collection, connectivity, _ = trajectory_catalog("AB")
    monkeypatch.setattr(
        topology_catalog_module,
        "_topology_bucket_digest",
        lambda topology: "forced-collision",
    )
    catalog = build_topology_catalog(collection, connectivity, tot_mapping())
    assert catalog.n_topologies == 2
    assert catalog.topologies[0].edge_keys != catalog.topologies[1].edge_keys


def test_undefined_consistency_and_unsupported_schema_are_rejected() -> None:
    _, _, catalog = trajectory_catalog("A")
    with pytest.raises(Exception, match="UNDEFINED"):
        replace(catalog, consistency=TopologyConsistency.UNDEFINED)
    payload = catalog.to_dict()
    payload["canonical_schema_version"] = "mdstats.topology-catalog.v999"
    with pytest.raises(Exception, match="serialized topology catalog"):
        TopologyCatalog.from_dict(payload)


def test_modified_serialized_digest_is_rejected() -> None:
    _, _, catalog = trajectory_catalog("AB")
    payload = catalog.to_dict()
    payload["digest"] = "0" * 64
    with pytest.raises(Exception, match="serialized topology catalog"):
        TopologyCatalog.from_dict(payload)
