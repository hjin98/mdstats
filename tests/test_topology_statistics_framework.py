"""TS2 tests for catalog-derived framework-topology statistics."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkBridgeSignature,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkStatisticsOptions,
    FrameworkTopologyStatistics,
    TopologyCatalogOptions,
    TopologyStatisticsConsistencyError,
    build_topology_catalog,
    compute_atomic_connectivity,
    compute_framework_topology_statistics,
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
            np.arange(n_frames, dtype=float) * 0.1
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


def tot_mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
        name="T-O-T",
    )


def make_catalog(
    sequence: str = "AABBA", *, semantics: FrameSemantics = FrameSemantics.TRAJECTORY
):
    collection = make_collection([14, 8, 13], len(sequence), semantics=semantics)
    edge_frames = {
        frame: ((AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)) if label == "A" else ())
        for frame, label in enumerate(sequence)
    }
    connectivity = compute_atomic_connectivity(
        collection, ExplicitConnectivity(frame_edges=edge_frames)
    )
    return build_topology_catalog(collection, connectivity, tot_mapping())


def test_graph_descriptors_are_exact_and_frame_resolved() -> None:
    result = compute_framework_topology_statistics(make_catalog())
    np.testing.assert_array_equal(result.descriptor("vertex_count").series.values, 2)
    np.testing.assert_array_equal(
        result.descriptor("edge_count").series.values, [1, 1, 0, 0, 1]
    )
    np.testing.assert_array_equal(
        result.descriptor("component_count").series.values, [1, 1, 2, 2, 1]
    )
    np.testing.assert_array_equal(
        result.descriptor("isolated_vertex_count").series.values, [0, 0, 2, 2, 0]
    )
    np.testing.assert_array_equal(result.descriptor("cycle_rank").series.values, 0)
    edge_dist = result.descriptor("edge_count").distribution
    np.testing.assert_array_equal(edge_dist.support, [0, 1])
    np.testing.assert_array_equal(edge_dist.frequencies, [2, 3])
    assert result.axis.x_label == "Frame index"


def test_endpoint_and_whole_path_bridge_statistics() -> None:
    result = compute_framework_topology_statistics(make_catalog())
    pair = result.endpoint_pair("Al", "Si")
    np.testing.assert_array_equal(pair.edge_count_series.values, [1, 1, 0, 0, 1])
    assert len(result.bridge_signature_statistics) == 1
    bridge = result.bridge_signature_statistics[0]
    assert bridge.signature.path_atomic_numbers == (13, 8, 14)
    assert bridge.signature.label == "Al-O-Si"
    np.testing.assert_array_equal(bridge.edge_count_series.values, [1, 1, 0, 0, 1])


def test_degree_statistics_are_species_resolved() -> None:
    result = compute_framework_topology_statistics(make_catalog())
    si = result.species_degree("Si")
    al = result.species_degree("Al")
    np.testing.assert_array_equal(si.degree_distribution.support, [0, 1])
    np.testing.assert_array_equal(si.degree_distribution.frequencies, [2, 3])
    np.testing.assert_allclose(si.per_vertex_mean_degree, [0.6])
    np.testing.assert_allclose(al.per_vertex_mean_degree, [0.6])
    np.testing.assert_array_equal(si.mean_degree_series.values, [1, 1, 0, 0, 1])


def test_framework_edge_occupancy_uses_canonical_edge_identity() -> None:
    result = compute_framework_topology_statistics(make_catalog())
    assert result.edge_occupancies is not None
    assert len(result.edge_occupancies) == 1
    occupancy = result.edge_occupancies[0]
    assert occupancy.frame_count == 3
    assert occupancy.probability == pytest.approx(0.6)
    assert result.edge_occupancy_summary is not None
    assert result.edge_occupancy_summary.mean == pytest.approx(0.6)


def test_catalog_occupancy_and_transition_aggregates() -> None:
    result = compute_framework_topology_statistics(make_catalog())
    assert result.n_topologies == 2
    np.testing.assert_array_equal(result.catalog_occupancy.state_frame_counts, [3, 2])
    changes = result.transition_statistics
    assert changes is not None
    assert changes.n_frame_boundaries == 4
    assert changes.n_changed_boundaries == 2
    assert changes.total_added_edges == 1
    assert changes.total_removed_edges == 1
    assert changes.total_edge_churn == 2
    assert changes.endpoint_pair_counts[0].label == "Al-Si"
    assert changes.endpoint_pair_counts[0].additions == 1
    assert changes.endpoint_pair_counts[0].removals == 1
    assert changes.bridge_signature_counts[0].additions == 1
    assert changes.bridge_signature_counts[0].removals == 1
    np.testing.assert_array_equal(changes.affected_vertex_atom_indices, [0, 2])
    np.testing.assert_array_equal(changes.affected_vertex_event_counts, [2, 2])
    np.testing.assert_array_equal(changes.affected_linker_atom_indices, [1])
    np.testing.assert_array_equal(changes.affected_linker_event_counts, [2])


def test_ensemble_has_static_statistics_but_no_transition_aggregates() -> None:
    result = compute_framework_topology_statistics(
        make_catalog("ABA", semantics=FrameSemantics.ENSEMBLE)
    )
    assert result.transition_statistics is None
    assert result.catalog_occupancy.visit_counts is None
    assert result.axis.x_label == "Sample index"
    np.testing.assert_array_equal(
        result.descriptor("edge_count").series.values, [1, 0, 1]
    )


def test_parallel_edge_descriptors_detect_distinct_linker_paths() -> None:
    collection = make_collection([14, 8, 8, 13], 1, semantics=FrameSemantics.ENSEMBLE)
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            uniform_edges=(
                AtomicEdgeKey(0, 1),
                AtomicEdgeKey(1, 3),
                AtomicEdgeKey(0, 2),
                AtomicEdgeKey(2, 3),
            )
        ),
    )
    catalog = build_topology_catalog(collection, connectivity, tot_mapping())
    result = compute_framework_topology_statistics(catalog)
    assert result.descriptor("edge_count").series.values[0] == 2
    assert result.descriptor("parallel_endpoint_pair_count").series.values[0] == 1
    assert result.descriptor("parallel_edge_excess_count").series.values[0] == 1
    assert result.descriptor("cycle_rank").series.values[0] == 1


def test_asymmetric_linker_order_remains_two_bridge_signatures() -> None:
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
    result = compute_framework_topology_statistics(
        build_topology_catalog(collection, connectivity, mapping)
    )
    assert len(result.bridge_signature_statistics) == 2
    signatures = {
        x.signature.path_atomic_numbers for x in result.bridge_signature_statistics
    }
    assert signatures == {(13, 16, 8, 14), (13, 8, 16, 14)}
    for item in result.bridge_signature_statistics:
        np.testing.assert_array_equal(item.edge_count_distribution.support, [0, 1])


def test_complete_reverse_bridge_signature_is_equal() -> None:
    first = FrameworkBridgeSignature.from_symbols(("Si", "O", "S", "Al"), rule_id="x")
    second = FrameworkBridgeSignature.from_symbols(("Al", "S", "O", "Si"), rule_id="x")
    swapped = FrameworkBridgeSignature.from_symbols(("Si", "S", "O", "Al"), rule_id="x")
    assert first == second
    assert first != swapped


def test_options_disable_optional_large_results() -> None:
    result = compute_framework_topology_statistics(
        make_catalog(),
        options=FrameworkStatisticsOptions(
            include_degree_statistics=False,
            include_edge_occupancies=False,
            include_transition_statistics=False,
        ),
    )
    assert result.degree_statistics is None
    assert result.edge_occupancies is None
    assert result.edge_occupancy_summary is None
    assert result.transition_statistics is None


def test_serialization_round_trip_and_digest_validation() -> None:
    result = compute_framework_topology_statistics(make_catalog())
    restored = FrameworkTopologyStatistics.from_dict(result.to_dict())
    assert restored.to_dict() == result.to_dict()
    assert restored.digest == result.digest
    payload = result.to_dict()
    payload["metadata"]["tampered"] = True
    with pytest.raises(TopologyStatisticsConsistencyError):
        FrameworkTopologyStatistics.from_dict(payload)


def test_arrays_are_defensively_copied_and_read_only() -> None:
    result = compute_framework_topology_statistics(make_catalog())
    assert not result.vertex_atom_indices.flags.writeable
    assert not result.descriptor("edge_count").topology_values.flags.writeable
    assert not result.species_degree("Si").per_vertex_mean_degree.flags.writeable
    with pytest.raises(ValueError):
        result.descriptor("edge_count").topology_values[0] = 7


def test_per_frame_catalog_is_summarized_without_temporal_transitions() -> None:
    collection = make_collection([14, 8, 13], 2, semantics=FrameSemantics.TRAJECTORY)
    connectivity = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(uniform_edges=(AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2))),
    )
    catalog = build_topology_catalog(
        collection,
        connectivity,
        tot_mapping(),
        catalog_options=TopologyCatalogOptions(mode="per_frame"),
    )
    result = compute_framework_topology_statistics(catalog)
    assert result.n_topologies == 2
    assert result.transition_statistics is None
    np.testing.assert_array_equal(result.descriptor("edge_count").series.values, [1, 1])


def test_wrong_input_and_ensemble_time_metadata_are_rejected() -> None:
    with pytest.raises(TypeError):
        compute_framework_topology_statistics(object())  # type: ignore[arg-type]
    with pytest.raises(TopologyStatisticsConsistencyError):
        compute_framework_topology_statistics(
            make_catalog("ABA", semantics=FrameSemantics.ENSEMBLE),
            times=[0.0, 1.0, 2.0],
            time_unit="ps",
        )
