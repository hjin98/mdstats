"""TS1 tests for catalog-derived atomic-connectivity statistics."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomicConnectivityStatistics,
    AtomicStatisticsOptions,
    AtomisticFrameCollection,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    TopologyStatisticsConsistencyError,
    TopologyStatisticsInputError,
    compute_atomic_connectivity,
    compute_atomic_connectivity_statistics,
)
from mdstats.analysis.atomic_connectivity import (
    AtomicConnectivityResult,
    AtomicConnectivityState,
    AtomicEdgeKey,
    ConnectivityConsistency,
    ResolvedConnectivityScope,
)


def make_collection(semantics: FrameSemantics) -> AtomisticFrameCollection:
    n_frames = 5
    atomic_numbers = np.asarray([14, 8, 13, 8, 11], dtype=np.int32)
    cells = np.repeat((np.eye(3) * 12.0)[None, ...], n_frames, axis=0)
    fractional = np.zeros((n_frames, atomic_numbers.size, 3), dtype=float)
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(100, 105, dtype=np.int64),
        atomic_numbers=atomic_numbers,
        masses=np.ones(atomic_numbers.size),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(0, 50, 10, dtype=np.int64)
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        times=np.arange(5, dtype=float) * 0.01
        if semantics is FrameSemantics.TRAJECTORY
        else None,
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros_like(fractional)
        if semantics is FrameSemantics.TRAJECTORY
        else None,
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


def make_catalog(semantics: FrameSemantics):
    si_o = AtomicEdgeKey(0, 1)
    al_o = AtomicEdgeKey(2, 3)
    na_o1 = AtomicEdgeKey(1, 4)
    na_o2 = AtomicEdgeKey(3, 4)
    frame_edges = {
        0: (si_o, al_o, na_o1),
        1: (si_o, al_o, na_o1, na_o2),
        2: (si_o, al_o, na_o1, na_o2),
        3: (si_o, al_o, na_o2),
        4: (si_o, al_o, na_o1),
    }
    return compute_atomic_connectivity(
        make_collection(semantics),
        ExplicitConnectivity(frame_edges=frame_edges),
    )


def test_pair_count_distributions_and_total_edge_series() -> None:
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY),
        steps=[0, 10, 20, 30, 40],
        times=[0.0, 0.01, 0.02, 0.03, 0.04],
        time_unit="ps",
    )
    np.testing.assert_array_equal(result.total_edge_series.values, [3, 4, 4, 3, 3])
    np.testing.assert_array_equal(result.total_edge_distribution.support, [3, 4])
    np.testing.assert_array_equal(result.total_edge_distribution.frequencies, [3, 2])

    si_o = result.pair("Si", "O")
    np.testing.assert_array_equal(si_o.contact_count_series.values, np.ones(5))
    np.testing.assert_array_equal(si_o.contact_count_distribution.support, [1])
    np.testing.assert_array_equal(si_o.contact_count_distribution.frequencies, [5])

    na_o = result.pair("Na", "O")
    np.testing.assert_array_equal(na_o.contact_count_series.values, [1, 2, 2, 1, 1])
    np.testing.assert_array_equal(na_o.contact_count_distribution.support, [1, 2])
    np.testing.assert_array_equal(na_o.contact_count_distribution.frequencies, [3, 2])
    assert na_o.contact_count_distribution.summary.mean == pytest.approx(1.4)
    assert na_o.contact_count_distribution.modes == (1,)
    assert result.axis.x_label == "Time (ps)"


def test_contact_occupancies_are_exact_and_pair_resolved() -> None:
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY)
    )
    na_o = result.pair("O", "Na")
    assert na_o.contact_occupancies is not None
    assert [
        (item.contact.pair, item.frame_count, item.probability)
        for item in na_o.contact_occupancies
    ] == [
        ((1, 4), 4, 0.8),
        ((3, 4), 3, 0.6),
    ]
    assert na_o.contact_occupancy_summary is not None
    assert na_o.contact_occupancy_summary.mean == pytest.approx(0.7)

    si_o = result.pair("Si", "O")
    assert si_o.contact_occupancies is not None
    assert len(si_o.contact_occupancies) == 1
    assert si_o.contact_occupancies[0].probability == 1.0


def test_explicit_zero_contact_pair_has_delta_zero_and_no_contact_occupancy() -> None:
    options = AtomicStatisticsOptions.from_species_pairs(
        [("Si", "Na")], include_degree_statistics=False
    )
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.ENSEMBLE), options=options
    )
    pair = result.pair("Na", "Si")
    np.testing.assert_array_equal(pair.contact_count_series.values, np.zeros(5))
    np.testing.assert_array_equal(pair.contact_count_distribution.support, [0])
    np.testing.assert_array_equal(pair.contact_count_distribution.frequencies, [5])
    assert pair.contact_occupancies == ()
    assert pair.contact_occupancy_summary is None


def test_species_degree_statistics_detect_mobile_na_coordination() -> None:
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY)
    )
    na = result.species_degree("Na")
    np.testing.assert_array_equal(na.atom_indices, [4])
    np.testing.assert_array_equal(na.degree_distribution.support, [1, 2])
    np.testing.assert_array_equal(na.degree_distribution.frequencies, [3, 2])
    np.testing.assert_array_equal(na.mean_degree_series.values, [1, 2, 2, 1, 1])
    np.testing.assert_allclose(na.per_atom_mean_degree, [1.4])
    np.testing.assert_allclose(
        na.per_atom_population_standard_deviation, [np.sqrt(0.24)]
    )

    si = result.species_degree("Si")
    assert si.degree_distribution.is_constant
    assert si.degree_distribution.summary.mean == 1.0


def test_catalog_occupancy_uses_unique_states_and_recurrence() -> None:
    catalog = make_catalog(FrameSemantics.TRAJECTORY)
    result = compute_atomic_connectivity_statistics(catalog)
    assert result.n_states == 3
    np.testing.assert_array_equal(
        result.catalog_occupancy.state_frame_counts, [2, 2, 1]
    )
    assert result.catalog_occupancy.visit_counts is not None
    np.testing.assert_array_equal(result.catalog_occupancy.visit_counts, [2, 1, 1])
    assert result.catalog_occupancy.effective_state_count > 1.0
    assert result.source_state_digests == tuple(
        state.digest for state in catalog.states
    )


def test_trajectory_transition_aggregates_count_additions_removals_and_atoms() -> None:
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY)
    )
    changes = result.transition_statistics
    assert changes is not None
    assert changes.n_frame_boundaries == 4
    assert changes.n_changed_boundaries == 3
    assert changes.total_added_edges == 2
    assert changes.total_removed_edges == 2
    assert changes.total_edge_churn == 4
    assert len(changes.pair_counts) == 1
    assert changes.pair_counts[0].label == "O-Na"
    assert changes.pair_counts[0].additions == 2
    assert changes.pair_counts[0].removals == 2
    np.testing.assert_array_equal(changes.affected_atom_indices, [1, 3, 4])
    np.testing.assert_array_equal(changes.affected_atom_event_counts, [2, 2, 3])


def test_ensemble_has_no_temporal_transition_statistics() -> None:
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.ENSEMBLE)
    )
    assert result.transition_statistics is None
    assert result.catalog_occupancy.visit_counts is None
    assert result.axis.x_label == "Sample index"


def test_options_can_disable_large_optional_results() -> None:
    options = AtomicStatisticsOptions(
        include_degree_statistics=False,
        include_contact_occupancies=False,
        include_transition_statistics=False,
    )
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY), options=options
    )
    assert result.degree_statistics is None
    assert result.transition_statistics is None
    assert all(item.contact_occupancies is None for item in result.pair_statistics)
    assert all(
        item.contact_occupancy_summary is None for item in result.pair_statistics
    )


def test_invalid_requested_species_pair_is_rejected() -> None:
    options = AtomicStatisticsOptions.from_species_pairs([("K", "O")])
    with pytest.raises(TopologyStatisticsInputError):
        compute_atomic_connectivity_statistics(
            make_catalog(FrameSemantics.ENSEMBLE), options=options
        )


def test_custom_quantiles_propagate_through_all_summaries() -> None:
    options = AtomicStatisticsOptions(quantiles=(0.0, 0.5, 1.0))
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY), options=options
    )
    np.testing.assert_array_equal(
        result.total_edge_distribution.summary.quantile_probabilities,
        [0.0, 0.5, 1.0],
    )
    np.testing.assert_array_equal(
        result.pair("Na", "O").contact_occupancy_summary.quantile_probabilities,
        [0.0, 0.5, 1.0],
    )


def test_result_serialization_round_trip_and_digest_validation() -> None:
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY)
    )
    restored = AtomicConnectivityStatistics.from_dict(result.to_dict())
    assert restored.to_dict() == result.to_dict()
    assert restored.digest == result.digest

    payload = result.to_dict()
    payload["metadata"]["tampered"] = True
    with pytest.raises(TopologyStatisticsConsistencyError):
        AtomicConnectivityStatistics.from_dict(payload)


def test_arrays_are_defensively_copied_and_read_only() -> None:
    result = compute_atomic_connectivity_statistics(
        make_catalog(FrameSemantics.TRAJECTORY)
    )
    assert not result.total_edge_series.values.flags.writeable
    assert not result.pair("Na", "O").state_contact_counts.flags.writeable
    assert not result.species_degree("Na").per_atom_mean_degree.flags.writeable
    with pytest.raises(ValueError):
        result.pair("Na", "O").state_contact_counts[0] = 99


def test_contact_occupancy_and_events_are_periodic_gauge_invariant() -> None:
    active = np.asarray([0, 1, 2], dtype=np.int64)
    numbers = np.asarray([14, 8, 13], dtype=np.int32)
    endpoints = np.asarray([[0, 1], [0, 2], [1, 2]], dtype=np.int64)
    common = dict(
        active_atom_indices=active,
        active_atomic_numbers=numbers,
        pbc=np.ones(3, dtype=bool),
        edge_atom_indices=endpoints,
        degree=np.asarray([2, 2, 2], dtype=np.int32),
        component_labels=np.zeros(3, dtype=np.int32),
        n_components=1,
    )
    state_a = AtomicConnectivityState(
        **common, edge_image_shifts=np.zeros((3, 3), dtype=np.int64)
    )
    shifts = np.zeros((3, 3), dtype=np.int64)
    shifts[2, 0] = 1
    state_b = AtomicConnectivityState(**common, edge_image_shifts=shifts)
    catalog = AtomicConnectivityResult(
        definition=ExplicitConnectivity(uniform_edges=()),
        resolved_scope=ResolvedConnectivityScope(
            atom_indices=active,
            atomic_numbers=numbers,
            canonical_key=("all",),
        ),
        consistency=ConnectivityConsistency.PARTITIONED,
        frame_indices=np.asarray([0, 1], dtype=np.int64),
        frame_ids=np.asarray([100, 101], dtype=np.int64),
        frame_state_ids=np.asarray([0, 1], dtype=np.int32),
        states=(state_a, state_b),
        segments=None,
        transitions=(),
        metadata={"frame_semantics": "trajectory"},
    )
    result = compute_atomic_connectivity_statistics(catalog)
    assert result.transition_statistics is not None
    assert result.transition_statistics.n_changed_boundaries == 0
    assert result.transition_statistics.total_edge_churn == 0
    assert (
        sum(len(item.contact_occupancies or ()) for item in result.pair_statistics) == 3
    )
    assert all(
        occupancy.probability == 1.0
        for item in result.pair_statistics
        for occupancy in (item.contact_occupancies or ())
    )


def test_wrong_input_and_time_metadata_are_rejected() -> None:
    with pytest.raises(TypeError):
        compute_atomic_connectivity_statistics(object())  # type: ignore[arg-type]
    with pytest.raises(TopologyStatisticsConsistencyError):
        compute_atomic_connectivity_statistics(
            make_catalog(FrameSemantics.ENSEMBLE),
            times=[0.0, 1.0, 2.0, 3.0, 4.0],
            time_unit="ps",
        )
