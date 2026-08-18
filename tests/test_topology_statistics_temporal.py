"""TS3 tests for exact trajectory-only topology temporal statistics."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomicStatisticsOptions,
    EntityPresenceStatistics,
    FrameSemantics,
    FrameworkStatisticsOptions,
    StateTransitionStatistics,
    TemporalStatisticsOptions,
    TopologyStatisticsConsistencyError,
    TopologyStatisticsInputError,
    build_frame_axis,
    compute_atomic_connectivity_statistics,
    compute_entity_presence_statistics,
    compute_framework_topology_statistics,
    compute_state_transition_statistics,
)

from .test_topology_statistics_atomic import make_catalog as make_atomic_catalog
from .test_topology_statistics_framework import make_catalog as make_framework_catalog


def trajectory_axis(n_frames: int = 5):
    return build_frame_axis(
        n_frames,
        frame_semantics=FrameSemantics.TRAJECTORY,
        collection_frame_indices=np.arange(n_frames),
        frame_ids=np.arange(100, 100 + n_frames),
        steps=np.arange(n_frames) * 10,
        times=np.arange(n_frames, dtype=float) * 0.1,
        time_unit="ps",
    )


def test_state_timeline_residence_intervals_and_transition_matrices() -> None:
    result = compute_state_transition_statistics(
        [0, 0, 1, 1, 0], trajectory_axis(), n_states=2
    )
    assert [
        (x.state_id, x.result_position_start, x.result_position_stop)
        for x in result.residence_intervals
    ] == [
        (0, 0, 2),
        (1, 2, 4),
        (0, 4, 5),
    ]
    assert [
        (x.source_state_id, x.target_state_id, x.result_position_after)
        for x in result.transition_events
    ] == [
        (0, 1, 2),
        (1, 0, 4),
    ]
    np.testing.assert_array_equal(result.adjacent_count_matrix, [[1, 1], [1, 1]])
    np.testing.assert_array_equal(result.changed_count_matrix, [[0, 1], [1, 0]])
    assert not result.adjacent_count_matrix.flags.writeable
    assert not result.frame_to_state_id.flags.writeable
    np.testing.assert_array_equal(
        result.cumulative_changed_boundaries.values, [0, 0, 1, 1, 2]
    )
    np.testing.assert_array_equal(result.dwell_frame_distribution.support, [1, 2])
    np.testing.assert_array_equal(result.dwell_frame_distribution.frequencies, [1, 2])


def test_state_recurrence_and_return_lags_are_exact() -> None:
    result = compute_state_transition_statistics(
        [0, 0, 1, 1, 0], trajectory_axis(), n_states=2
    )
    state_zero = result.state(0)
    assert state_zero.n_visits == 2
    assert state_zero.total_frames == 3
    np.testing.assert_array_equal(state_zero.return_frame_lags, [3])
    np.testing.assert_allclose(state_zero.return_time_lags, [0.3])
    assert state_zero.return_frame_lag_distribution is not None
    assert state_zero.return_frame_lag_distribution.support.tolist() == [3]
    assert state_zero.return_time_lag_summary is not None
    assert state_zero.return_time_lag_summary.mean == pytest.approx(0.3)


def test_uniform_and_single_frame_trajectories_are_valid() -> None:
    uniform = compute_state_transition_statistics(
        [0, 0, 0], trajectory_axis(3), n_states=1
    )
    assert uniform.n_intervals == 1
    assert uniform.n_changed_boundaries == 0
    np.testing.assert_array_equal(uniform.adjacent_count_matrix, [[2]])
    np.testing.assert_array_equal(uniform.changed_count_matrix, [[0]])

    single = compute_state_transition_statistics([0], trajectory_axis(1), n_states=1)
    assert single.residence_intervals[0].n_frames == 1
    assert single.residence_intervals[0].time_span == 0.0
    assert single.dwell_time_span_summary is not None
    assert single.dwell_time_span_summary.mean == 0.0


def test_temporal_functions_reject_ensemble_axes() -> None:
    axis = build_frame_axis(3, frame_semantics=FrameSemantics.ENSEMBLE)
    with pytest.raises(TopologyStatisticsInputError):
        compute_state_transition_statistics([0, 1, 0], axis)
    with pytest.raises(TopologyStatisticsInputError):
        compute_entity_presence_statistics(((0,), (1,)), [0, 1, 0], axis)


def test_entity_presence_episodes_and_censoring() -> None:
    result = compute_entity_presence_statistics(
        ((0,), (0, 1), (1,)),
        [0, 1, 1, 2, 0],
        trajectory_axis(),
        n_entities=2,
    )
    assert result.entity_episode_counts.tolist() == [2, 1]
    assert result.entity_total_frame_counts.tolist() == [4, 3]
    np.testing.assert_allclose(result.entity_occupancy_probabilities, [0.8, 0.6])
    entity_zero = result.episodes_for(0)
    assert [(x.result_position_start, x.result_position_stop) for x in entity_zero] == [
        (0, 3),
        (4, 5),
    ]
    assert entity_zero[0].left_censored and not entity_zero[0].right_censored
    assert entity_zero[1].right_censored and not entity_zero[1].left_censored
    entity_one = result.episodes_for(1)
    assert [(x.result_position_start, x.result_position_stop) for x in entity_one] == [
        (1, 4)
    ]


def test_temporal_results_round_trip_and_detect_digest_tampering() -> None:
    state = compute_state_transition_statistics(
        [0, 1, 0], trajectory_axis(3), n_states=2
    )
    restored = StateTransitionStatistics.from_dict(state.to_dict())
    assert restored.to_dict() == state.to_dict()
    payload = state.to_dict()
    payload["metadata"]["tampered"] = True
    with pytest.raises(TopologyStatisticsConsistencyError):
        StateTransitionStatistics.from_dict(payload)

    entities = compute_entity_presence_statistics(
        ((0,), ()), [0, 1, 0], trajectory_axis(3), n_entities=1
    )
    restored_entities = EntityPresenceStatistics.from_dict(entities.to_dict())
    assert restored_entities.to_dict() == entities.to_dict()


def test_atomic_statistics_integrate_state_timeline_and_contact_episodes() -> None:
    result = compute_atomic_connectivity_statistics(
        make_atomic_catalog(FrameSemantics.TRAJECTORY)
    )
    temporal = result.temporal_statistics
    assert temporal is not None
    assert temporal.state_statistics.n_changed_boundaries == 3
    assert [
        x.result_position_after for x in temporal.state_statistics.transition_events
    ] == [1, 3, 4]
    contact = next(key for key in temporal.contact_keys if key.pair == (1, 4))
    episodes = temporal.contact_episode_statistics(contact)
    assert [(x.result_position_start, x.result_position_stop) for x in episodes] == [
        (0, 3),
        (4, 5),
    ]
    assert result.transition_statistics is not None
    assert (
        result.transition_statistics.n_changed_boundaries
        == temporal.state_statistics.n_changed_boundaries
    )


def test_framework_statistics_integrate_class_timeline_and_edge_episodes() -> None:
    result = compute_framework_topology_statistics(make_framework_catalog())
    temporal = result.temporal_statistics
    assert temporal is not None
    assert temporal.state_statistics.n_changed_boundaries == 2
    assert [
        x.result_position_after for x in temporal.state_statistics.transition_events
    ] == [2, 4]
    assert len(temporal.edge_keys) == 1
    episodes = temporal.edge_episode_statistics(temporal.edge_keys[0])
    assert [(x.result_position_start, x.result_position_stop) for x in episodes] == [
        (0, 2),
        (4, 5),
    ]


def test_ensemble_branches_remain_non_temporal() -> None:
    atomic = compute_atomic_connectivity_statistics(
        make_atomic_catalog(FrameSemantics.ENSEMBLE)
    )
    framework = compute_framework_topology_statistics(
        make_framework_catalog("ABA", semantics=FrameSemantics.ENSEMBLE)
    )
    assert atomic.temporal_statistics is None
    assert framework.temporal_statistics is None


def test_options_can_disable_detailed_temporal_results() -> None:
    atomic = compute_atomic_connectivity_statistics(
        make_atomic_catalog(FrameSemantics.TRAJECTORY),
        options=AtomicStatisticsOptions(include_temporal_statistics=False),
    )
    framework = compute_framework_topology_statistics(
        make_framework_catalog(),
        options=FrameworkStatisticsOptions(include_temporal_statistics=False),
    )
    assert atomic.temporal_statistics is None
    assert framework.temporal_statistics is None


def test_entity_episode_options_use_requested_quantiles() -> None:
    options = TemporalStatisticsOptions(quantiles=(0.0, 0.5, 1.0))
    result = compute_entity_presence_statistics(
        ((0,), ()),
        [0, 0, 1, 0],
        trajectory_axis(4),
        n_entities=1,
        options=options,
    )
    assert result.episode_frame_length_distribution is not None
    np.testing.assert_array_equal(
        result.episode_frame_length_distribution.summary.quantile_probabilities,
        [0.0, 0.5, 1.0],
    )
