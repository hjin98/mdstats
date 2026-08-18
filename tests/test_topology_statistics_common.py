"""TS0 tests for graph-independent topology-statistics primitives."""

from __future__ import annotations

import math

import numpy as np
import pytest

from mdstats import (
    CANONICAL_TOPOLOGY_STATISTICS_COMMON_SCHEMA,
    CatalogOccupancyStatistics,
    DiscreteCountDistribution,
    FrameAxis,
    FrameSemantics,
    ScalarSeries,
    ScalarSummary,
    TopologyStatisticsConsistencyError,
    TopologyStatisticsInputError,
    TopologyStatisticsSerializationError,
    build_frame_axis,
    build_scalar_series,
    canonical_statistics_json,
    compute_catalog_occupancy_statistics,
    compute_discrete_count_distribution,
    compute_scalar_summary,
    expand_state_values_to_frames,
    topology_statistics_payload_digest,
)


def test_scalar_summary_uses_population_standard_deviation() -> None:
    summary = compute_scalar_summary([1, 2, 3, 4])
    assert summary.count == 4
    assert summary.mean == 2.5
    assert summary.population_standard_deviation == pytest.approx(np.sqrt(1.25))
    assert summary.median == 2.5
    np.testing.assert_allclose(summary.quantile_values, [1.0, 1.75, 2.5, 3.25, 4.0])
    assert not summary.is_constant
    assert not summary.quantile_values.flags.writeable


def test_constant_scalar_summary_has_exact_zero_width() -> None:
    summary = compute_scalar_summary(np.full(5, 96, dtype=np.int64))
    assert summary.is_constant
    assert summary.population_standard_deviation == 0.0
    assert summary.minimum == summary.maximum == summary.mean == 96.0


def test_scalar_summary_rejects_empty_nonfinite_and_bad_quantiles() -> None:
    with pytest.raises(TopologyStatisticsInputError):
        compute_scalar_summary([])
    with pytest.raises(TopologyStatisticsInputError):
        compute_scalar_summary([1.0, np.nan])
    with pytest.raises(TopologyStatisticsInputError):
        compute_scalar_summary([1, 2], quantiles=(0.0, 0.5, 0.5, 1.0))
    with pytest.raises(TopologyStatisticsInputError):
        compute_scalar_summary([1, 2], quantiles=(0.1, 1.0))


def test_exact_discrete_count_distribution_constant_delta_function() -> None:
    distribution = compute_discrete_count_distribution(
        np.full(2000, 96, dtype=np.int64)
    )
    np.testing.assert_array_equal(distribution.support, [96])
    np.testing.assert_array_equal(distribution.frequencies, [2000])
    np.testing.assert_array_equal(distribution.probabilities, [1.0])
    assert distribution.modes == (96,)
    assert distribution.frequency_for(96) == 2000
    assert distribution.probability_for(96) == 1.0
    assert distribution.frequency_for(95) == 0
    assert distribution.is_constant


def test_exact_discrete_distribution_preserves_all_modes() -> None:
    distribution = compute_discrete_count_distribution([2, 2, 3, 3, 4])
    np.testing.assert_array_equal(distribution.support, [2, 3, 4])
    np.testing.assert_array_equal(distribution.frequencies, [2, 2, 1])
    assert distribution.modes == (2, 3)
    assert distribution.summary.mean == pytest.approx(2.8)


def test_discrete_count_distribution_rejects_negative_float_bool_and_empty() -> None:
    for values in ([-1, 0], [1.0, 2.0], [True, False], []):
        with pytest.raises(TopologyStatisticsInputError):
            compute_discrete_count_distribution(values)


def test_trajectory_catalog_occupancy_reports_visits_and_recurrence() -> None:
    occupancy = compute_catalog_occupancy_statistics(
        [0, 0, 1, 1, 0],
        frame_semantics=FrameSemantics.TRAJECTORY,
    )
    np.testing.assert_array_equal(occupancy.state_frame_counts, [3, 2])
    np.testing.assert_allclose(occupancy.state_probabilities, [0.6, 0.4])
    np.testing.assert_array_equal(occupancy.first_result_positions, [0, 2])
    np.testing.assert_array_equal(occupancy.last_result_positions, [4, 3])
    assert occupancy.visit_counts is not None
    np.testing.assert_array_equal(occupancy.visit_counts, [2, 1])
    assert occupancy.dominant_state_ids == (0,)
    assert occupancy.singleton_state_ids == ()
    assert occupancy.n_frames == 5
    assert occupancy.n_states == 2
    assert occupancy.n_observed_states == 2
    assert occupancy.shannon_state_entropy == pytest.approx(
        -(0.6 * math.log(0.6) + 0.4 * math.log(0.4))
    )
    assert occupancy.effective_state_count == pytest.approx(
        math.exp(occupancy.shannon_state_entropy)
    )


def test_ensemble_occupancy_has_no_temporal_visit_counts() -> None:
    occupancy = compute_catalog_occupancy_statistics(
        [1, 0, 1],
        frame_semantics=FrameSemantics.ENSEMBLE,
    )
    assert occupancy.visit_counts is None
    np.testing.assert_array_equal(occupancy.state_frame_counts, [1, 2])
    assert occupancy.singleton_state_ids == (0,)


def test_occupancy_can_preserve_unobserved_declared_states() -> None:
    occupancy = compute_catalog_occupancy_statistics(
        [0, 2, 2],
        frame_semantics=FrameSemantics.ENSEMBLE,
        n_states=4,
    )
    np.testing.assert_array_equal(occupancy.state_frame_counts, [1, 0, 2, 0])
    np.testing.assert_array_equal(occupancy.first_result_positions, [0, -1, 1, -1])
    assert occupancy.unobserved_state_ids == (1, 3)
    assert occupancy.n_observed_states == 2
    assert occupancy.frame_groups[1].frame_count == 0


def test_uniform_occupancy_has_zero_entropy_and_one_effective_state() -> None:
    occupancy = compute_catalog_occupancy_statistics(
        [0, 0, 0],
        frame_semantics=FrameSemantics.TRAJECTORY,
    )
    assert occupancy.shannon_state_entropy == 0.0
    assert occupancy.effective_state_count == 1.0


def test_occupancy_rejects_invalid_state_ids_or_state_count() -> None:
    with pytest.raises(TopologyStatisticsInputError):
        compute_catalog_occupancy_statistics(
            [-1, 0], frame_semantics=FrameSemantics.ENSEMBLE
        )
    with pytest.raises(TopologyStatisticsInputError):
        compute_catalog_occupancy_statistics(
            [0, 2], frame_semantics=FrameSemantics.ENSEMBLE, n_states=2
        )


def test_frame_axis_trajectory_prefers_time_then_steps_then_frames() -> None:
    axis = build_frame_axis(
        3,
        frame_semantics=FrameSemantics.TRAJECTORY,
        collection_frame_indices=[2, 4, 6],
        frame_ids=[102, 104, 106],
        steps=[20, 40, 60],
        times=[0.02, 0.04, 0.06],
        time_unit="ps",
    )
    np.testing.assert_allclose(axis.x_values, [0.02, 0.04, 0.06])
    assert axis.x_label == "Time (ps)"
    assert axis.has_physical_time
    assert not axis.collection_frame_indices.flags.writeable

    step_axis = build_frame_axis(
        2,
        frame_semantics=FrameSemantics.TRAJECTORY,
        steps=[10, 20],
    )
    np.testing.assert_array_equal(step_axis.x_values, [10, 20])
    assert step_axis.x_label == "Simulation step"


def test_frame_axis_ensemble_is_sample_only() -> None:
    axis = build_frame_axis(3, frame_semantics=FrameSemantics.ENSEMBLE)
    np.testing.assert_array_equal(axis.x_values, [0, 1, 2])
    assert axis.x_label == "Sample index"
    with pytest.raises(TopologyStatisticsConsistencyError):
        build_frame_axis(
            3,
            frame_semantics=FrameSemantics.ENSEMBLE,
            times=[0.0, 1.0, 2.0],
            time_unit="ps",
        )


def test_frame_axis_rejects_nonmonotonic_trajectory_metadata() -> None:
    with pytest.raises(TopologyStatisticsConsistencyError):
        build_frame_axis(
            3,
            frame_semantics=FrameSemantics.TRAJECTORY,
            collection_frame_indices=[0, 2, 1],
        )
    with pytest.raises(TopologyStatisticsConsistencyError):
        build_frame_axis(
            3,
            frame_semantics=FrameSemantics.TRAJECTORY,
            times=[0.0, 0.1, 0.1],
            time_unit="ps",
        )
    with pytest.raises(TopologyStatisticsConsistencyError):
        build_frame_axis(
            2,
            frame_semantics=FrameSemantics.TRAJECTORY,
            times=[0.0, 1.0],
        )


def test_scalar_series_is_immutable_aligned_and_round_trips() -> None:
    axis = build_frame_axis(3, frame_semantics=FrameSemantics.TRAJECTORY)
    series = build_scalar_series("Na-O contacts", [114, 116, 115], axis, unit="edges")
    assert series.is_integer
    assert series.summary.mean == 115.0
    assert not series.values.flags.writeable
    restored = ScalarSeries.from_dict(series.to_dict())
    assert restored.to_dict() == series.to_dict()

    with pytest.raises(TopologyStatisticsConsistencyError):
        build_scalar_series("bad", [1, 2], axis)


def test_state_value_expansion_preserves_trailing_shape_and_dtype() -> None:
    scalar = expand_state_values_to_frames([10, 20], [0, 1, 0])
    np.testing.assert_array_equal(scalar, [10, 20, 10])
    assert scalar.dtype == np.int64
    assert not scalar.flags.writeable

    vector = expand_state_values_to_frames(
        np.asarray([[1.0, 2.0], [3.0, 4.0]]),
        [1, 0, 1],
    )
    np.testing.assert_allclose(vector, [[3.0, 4.0], [1.0, 2.0], [3.0, 4.0]])
    assert not vector.flags.writeable


def test_state_value_expansion_rejects_invalid_leading_axis_or_assignment() -> None:
    with pytest.raises(TopologyStatisticsInputError):
        expand_state_values_to_frames(3, [0])
    with pytest.raises(TopologyStatisticsInputError):
        expand_state_values_to_frames([1, 2], [0, 2])


def test_common_result_serialization_round_trips() -> None:
    objects = [
        compute_scalar_summary([1, 2, 3]),
        compute_discrete_count_distribution([1, 1, 2]),
        compute_catalog_occupancy_statistics(
            [0, 1, 0], frame_semantics=FrameSemantics.TRAJECTORY
        ),
        build_frame_axis(2, frame_semantics=FrameSemantics.ENSEMBLE),
    ]
    types = [
        ScalarSummary,
        DiscreteCountDistribution,
        CatalogOccupancyStatistics,
        FrameAxis,
    ]
    for value, result_type in zip(objects, types, strict=True):
        restored = result_type.from_dict(value.to_dict())
        assert restored.to_dict() == value.to_dict()
        assert (
            value.to_dict()["schema_version"]
            == CANONICAL_TOPOLOGY_STATISTICS_COMMON_SCHEMA
        )


def test_serialization_rejects_wrong_schema_or_object_type() -> None:
    payload = compute_scalar_summary([1, 2]).to_dict()
    payload["schema_version"] = "wrong"
    with pytest.raises(TopologyStatisticsSerializationError):
        ScalarSummary.from_dict(payload)

    payload = compute_scalar_summary([1, 2]).to_dict()
    payload["object_type"] = "FrameAxis"
    with pytest.raises(TopologyStatisticsSerializationError):
        ScalarSummary.from_dict(payload)


def test_canonical_json_and_digest_are_order_independent() -> None:
    left = {"b": [2, 3], "a": 1}
    right = {"a": 1, "b": [2, 3]}
    assert canonical_statistics_json(left) == canonical_statistics_json(right)
    assert topology_statistics_payload_digest(
        left
    ) == topology_statistics_payload_digest(right)
    assert len(topology_statistics_payload_digest(left)) == 64


def test_public_ts0_types_are_importable_from_mdstats() -> None:
    assert ScalarSummary.__module__.endswith("topology_statistics._common")
    assert DiscreteCountDistribution.__module__.endswith("topology_statistics._common")
    assert CatalogOccupancyStatistics.__module__.endswith("topology_statistics._common")


def test_common_results_defensively_copy_caller_arrays() -> None:
    source = np.asarray([1, 2, 3], dtype=np.int64)
    distribution = compute_discrete_count_distribution(source)
    axis = build_frame_axis(
        3,
        frame_semantics=FrameSemantics.TRAJECTORY,
        collection_frame_indices=source,
    )
    source[:] = 99
    np.testing.assert_array_equal(distribution.support, [1, 2, 3])
    np.testing.assert_array_equal(axis.collection_frame_indices, [1, 2, 3])
