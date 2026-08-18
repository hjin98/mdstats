from __future__ import annotations

import numpy as np
import pytest

import mdstats
from mdstats.sampling import (
    AutocorrelationEstimate,
    AutocorrelationEstimateStatus,
    AutocorrelationPolicy,
    BalancedAssignmentPlan,
    CompleteFrameBlockPlan,
    CompleteFrameBlockPolicy,
    PurgedKFoldPlan,
    PurgedKFoldPolicy,
    SamplingInputError,
    assign_balanced_round_robin,
    build_complete_frame_block_plan,
    build_purged_kfold_plan,
    contiguous_frame_runs,
    effective_sample_count,
    estimate_autocorrelation,
    integrated_autocorrelation_time,
    purge_neighbor_positions,
    split_frame_interval,
)


def _legacy_tau(values: np.ndarray) -> float:
    vector = np.asarray(values, dtype=np.float64)
    n = int(vector.size)
    if n < 3:
        return 0.5
    centered = vector - np.mean(vector)
    variance = float(np.dot(centered, centered) / n)
    if variance <= np.finfo(np.float64).eps:
        return 0.5
    size = 1 << (2 * n - 1).bit_length()
    transformed = np.fft.rfft(centered, n=size)
    acov = np.fft.irfft(transformed * np.conjugate(transformed), n=size)[:n]
    acov /= np.arange(n, 0, -1, dtype=np.float64)
    rho = acov / acov[0]
    tau = 0.5
    index = 1
    while index < n:
        if index + 1 < n:
            pair = float(rho[index] + rho[index + 1])
            if pair <= 0.0:
                break
            tau += pair
            index += 2
        else:
            if rho[index] <= 0.0:
                break
            tau += float(rho[index])
            index += 1
    return max(0.5, min(float(tau), 0.5 * n))


def test_autocorrelation_matches_frozen_stat1_samp0_oracle_exactly() -> None:
    rng = np.random.default_rng(731)
    for size in (1, 2, 3, 4, 5, 17, 128, 513):
        samples = [rng.normal(size=size) for _ in range(12)]
        samples.append(np.ones(size))
        for values in samples:
            assert integrated_autocorrelation_time(values) == _legacy_tau(values)


def test_autocorrelation_status_effective_count_and_round_trip() -> None:
    short = estimate_autocorrelation([1.0, 2.0])
    assert short.status is AutocorrelationEstimateStatus.INSUFFICIENT
    assert short.autocorrelation_time_frames == 0.5
    assert short.effective_sample_count == 2.0

    constant = estimate_autocorrelation(np.ones(32))
    assert constant.status is AutocorrelationEstimateStatus.CONSTANT
    assert constant.effective_sample_count == 32.0

    rng = np.random.default_rng(11)
    correlated = np.cumsum(rng.normal(size=256))
    result = estimate_autocorrelation(correlated)
    assert result.status is AutocorrelationEstimateStatus.ESTIMATED
    assert result.autocorrelation_time_frames > 0.5
    assert result.effective_sample_count < result.observation_count
    assert AutocorrelationEstimate.from_dict(result.to_dict()) == result
    assert AutocorrelationPolicy.from_dict(AutocorrelationPolicy().to_dict()) == AutocorrelationPolicy()
    assert effective_sample_count(20, 2.0) == pytest.approx(5.0)


def test_autocorrelation_rejects_nonfinite_and_multidimensional_input() -> None:
    with pytest.raises(SamplingInputError, match="one-dimensional"):
        estimate_autocorrelation(np.ones((2, 2)))
    with pytest.raises(SamplingInputError, match="finite"):
        estimate_autocorrelation([1.0, np.nan, 2.0])


def test_complete_frame_plan_never_crosses_gaps_and_retains_all_frames() -> None:
    eligible = np.array([0, 1, 2, 3, 8, 9, 10, 11, 12], dtype=np.int64)
    observable = np.arange(13, dtype=np.float64)
    plan = build_complete_frame_block_plan(
        eligible_frame_indices=eligible,
        frame_observables={"energy": observable},
        policy=CompleteFrameBlockPolicy(
            minimum_block_frames=2,
            explicit_block_length_frames=2,
        ),
    )
    assert [(run.frame_start, run.frame_stop) for run in plan.contiguous_runs] == [
        (0, 4),
        (8, 13),
    ]
    flattened = [
        frame
        for interval in plan.block_intervals
        for frame in range(interval.frame_start, interval.frame_stop)
    ]
    assert flattened == eligible.tolist()
    assert all(
        not (interval.frame_start < 8 < interval.frame_stop)
        for interval in plan.block_intervals
    )
    assert CompleteFrameBlockPlan.from_dict(plan.to_dict()) == plan


def test_balanced_interval_split_matches_historical_remainder_rule() -> None:
    intervals = split_frame_interval(0, 100, 32)
    assert [(item.frame_start, item.frame_stop) for item in intervals] == [
        (0, 34),
        (34, 67),
        (67, 100),
    ]
    assert contiguous_frame_runs([0, 1, 4, 5, 6]) == (
        mdstats.FrameInterval(0, 2),
        mdstats.FrameInterval(4, 7),
    )


def test_complete_frame_plan_records_short_explicit_override() -> None:
    values = np.cumsum(np.ones(64))
    plan = build_complete_frame_block_plan(
        eligible_frame_indices=np.arange(64),
        frame_observables={"slow": values},
        policy=CompleteFrameBlockPolicy(
            minimum_block_frames=4,
            autocorrelation_block_multiplier=2.0,
            explicit_block_length_frames=4,
        ),
    )
    assert plan.explicit_length_override
    assert plan.resolved_block_length_frames == 4
    assert plan.decorrelation_target_length_frames > 4
    assert any("shorter" in note for note in plan.notes)


def test_balanced_round_robin_is_stable_complete_and_balanced() -> None:
    plan = assign_balanced_round_robin(
        tuple(f"b{i}" for i in range(10)), ("train", "valid", "test")
    )
    assert plan.items_for("train") == ("b0", "b3", "b6", "b9")
    assert plan.items_for("valid") == ("b1", "b4", "b7")
    assert plan.items_for("test") == ("b2", "b5", "b8")
    assert BalancedAssignmentPlan.from_dict(plan.to_dict()) == plan


def test_purged_kfold_roles_are_disjoint_complete_and_deterministic() -> None:
    items = tuple(f"block-{index}" for index in range(12))
    policy = PurgedKFoldPolicy(requested_fold_count=4, purge_radius_items=1)
    first = build_purged_kfold_plan(items, policy=policy)
    second = build_purged_kfold_plan(items, policy=policy)
    assert first == second
    assert PurgedKFoldPlan.from_dict(first.to_dict()) == first
    assert first.omitted_fold_indices == ()
    for fold in first.folds:
        training = set(fold.training_item_ids)
        evaluation = set(fold.evaluation_item_ids)
        purged = set(fold.purged_item_ids)
        assert not training & evaluation
        assert not training & purged
        assert not evaluation & purged
        assert training | evaluation | purged == set(items)


def test_purge_neighbors_respect_boundaries() -> None:
    assert purge_neighbor_positions([0, 4], item_count=5, purge_radius_items=1) == (1, 3)
    with pytest.raises(SamplingInputError):
        purge_neighbor_positions([], item_count=5, purge_radius_items=1)


def test_sampling_primitives_are_public() -> None:
    assert mdstats.estimate_autocorrelation is estimate_autocorrelation
    assert mdstats.build_complete_frame_block_plan is build_complete_frame_block_plan
    assert mdstats.build_purged_kfold_plan is build_purged_kfold_plan
    assert "CompleteFrameBlockPlan" in mdstats.__all__


def test_autocorrelation_policy_rejects_inconsistent_tau_bounds() -> None:
    with pytest.raises(SamplingInputError, match="incompatible"):
        AutocorrelationPolicy(
            minimum_observations=3,
            minimum_tau_frames=2.0,
            maximum_tau_fraction=0.5,
        )


def test_block_plan_ignores_nonfinite_values_outside_eligible_frames() -> None:
    eligible = np.array([2, 3, 7, 8], dtype=np.int64)
    values = np.array([np.nan, np.nan, 1.0, 2.0, np.nan, np.nan, np.nan, 3.0, 4.0])
    plan = build_complete_frame_block_plan(
        eligible_frame_indices=eligible,
        frame_observables={"energy": values},
        policy=CompleteFrameBlockPolicy(explicit_block_length_frames=2),
    )
    assert plan.eligible_frame_indices == tuple(eligible)


def test_signed_records_reject_tampering() -> None:
    estimate = estimate_autocorrelation(np.arange(16, dtype=float))
    payload = estimate.to_dict()
    payload["effective_sample_count"] = 1.25
    with pytest.raises(Exception, match="signature mismatch"):
        AutocorrelationEstimate.from_dict(payload)

    plan = build_purged_kfold_plan(
        tuple(f"item-{index}" for index in range(8)),
        policy=PurgedKFoldPolicy(requested_fold_count=4, purge_radius_items=1),
    )
    payload = plan.to_dict()
    payload["omitted_fold_indices"] = [0]
    with pytest.raises(Exception):
        PurgedKFoldPlan.from_dict(payload)
