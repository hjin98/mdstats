"""LD0-R2 registration, periodic-mean, spread, and resolution diagnostics."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    PeriodicMeanPolicy,
    evaluate_cell_equivalence,
    periodic_frechet_mean_diagnostic,
    periodic_item_spread_diagnostics,
    reciprocal_resolution_diagnostic,
)


def test_cell_equivalence_uses_declared_frobenius_tolerance() -> None:
    display = np.eye(3) * 10.0
    equivalent = np.repeat(display[None, :, :], 2, axis=0)
    equivalent[1, 0, 0] += 5.0e-10
    report = evaluate_cell_equivalence(equivalent, display)
    assert report.equivalent is True
    assert report.maximum_mismatch_frame_position == 1
    assert report.maximum_mismatch <= report.tolerance

    different = np.array(equivalent, copy=True)
    different[1, 0, 0] += 1.0e-6
    report = evaluate_cell_equivalence(different, display)
    assert report.equivalent is False
    assert report.maximum_mismatch > report.tolerance


def test_reciprocal_resolution_matches_orthogonal_longest_interval() -> None:
    cell = np.diag([10.0, 20.0, 30.0])
    diagnostic = reciprocal_resolution_diagnostic(cell, (10, 10, 10))
    assert diagnostic.reciprocal_interval == pytest.approx(3.0, rel=2.0e-14)
    np.testing.assert_array_equal(diagnostic.integer_vector, [0, 0, 1])
    assert diagnostic.shortest_vector_norm == pytest.approx(2.0 * np.pi / 3.0)


def test_reciprocal_resolution_matches_exhaustive_skew_reference() -> None:
    cell = np.asarray(
        [[8.0, 0.0, 0.0], [3.0, 7.0, 0.0], [2.0, 1.5, 6.5]],
        dtype=float,
    )
    shape = (11, 9, 8)
    diagnostic = reciprocal_resolution_diagnostic(cell, shape)
    basis = 2.0 * np.pi * (np.diag(shape) @ np.linalg.inv(cell).T)
    brute = min(
        np.linalg.norm(np.asarray([i, j, k], dtype=float) @ basis)
        for i in range(-6, 7)
        for j in range(-6, 7)
        for k in range(-6, 7)
        if (i, j, k) != (0, 0, 0)
    )
    assert diagnostic.shortest_vector_norm == pytest.approx(brute, rel=2.0e-14)


def test_periodic_mean_crossing_is_converged_and_deterministic() -> None:
    samples = np.asarray([[0.99, 0.5, 0.5], [0.01, 0.5, 0.5]])
    kwargs = {
        "weights": np.asarray([0.5, 0.5]),
        "cell": np.eye(3) * 10.0,
        "pbc": np.ones(3, dtype=bool),
    }
    first = periodic_frechet_mean_diagnostic(samples, **kwargs)
    second = periodic_frechet_mean_diagnostic(samples + [2.0, -1.0, 3.0], **kwargs)
    assert first.mean_converged is True
    assert first.mean_ambiguity_detected is False
    assert first.final_update_norm <= 1.0e-11
    np.testing.assert_allclose(first.mean_cartesian, second.mean_cartesian, atol=2.0e-12)
    assert min(first.mean_fractional[0], 1.0 - first.mean_fractional[0]) <= 2.0e-14


def test_periodic_mean_detects_antipodal_ambiguity() -> None:
    diagnostic = periodic_frechet_mean_diagnostic(
        np.asarray([[0.25, 0.5, 0.5], [0.75, 0.5, 0.5]]),
        weights=np.asarray([0.5, 0.5]),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
    )
    assert diagnostic.mean_converged is True
    assert diagnostic.mean_ambiguity_detected is True
    assert diagnostic.candidate_solution_count == 2
    assert diagnostic.valid_for_reference is False


def test_periodic_mean_reports_nonconvergence() -> None:
    diagnostic = periodic_frechet_mean_diagnostic(
        np.asarray([[0.1, 0.5, 0.5], [0.2, 0.5, 0.5], [0.9, 0.5, 0.5]]),
        weights=np.full(3, 1.0 / 3.0),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
        policy=PeriodicMeanPolicy(max_iterations=1),
    )
    assert diagnostic.mean_converged is False
    assert diagnostic.iteration_count == 1
    assert diagnostic.valid_for_reference is False


def test_spread_reference_excludes_ambiguous_items() -> None:
    samples = np.asarray(
        [
            [[0.49, 0.5, 0.5], [0.25, 0.5, 0.5]],
            [[0.51, 0.5, 0.5], [0.75, 0.5, 0.5]],
        ]
    )
    diagnostics = periodic_item_spread_diagnostics(
        samples,
        weights=np.asarray([0.5, 0.5]),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
        quantile=0.10,
    )
    np.testing.assert_array_equal(diagnostics.valid_reference_mask, [True, False])
    assert diagnostics.valid_reference_count == 1
    assert diagnostics.required_reference_count == 1
    assert diagnostics.reference_standard_deviation == pytest.approx(
        0.1 / np.sqrt(3.0)
    )

    strict = periodic_item_spread_diagnostics(
        samples,
        weights=np.asarray([0.5, 0.5]),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
        quantile=0.10,
        policy=PeriodicMeanPolicy(minimum_valid_reference_fraction=1.0),
    )
    assert strict.reference_standard_deviation is None
    assert strict.insufficient_valid_reference is True


def test_zero_spread_has_no_finite_adaptive_target() -> None:
    samples = np.repeat(np.asarray([[[0.2, 0.3, 0.4]]]), 3, axis=0)
    diagnostics = periodic_item_spread_diagnostics(
        samples,
        weights=np.full(3, 1.0 / 3.0),
        cell=np.eye(3) * 10.0,
        pbc=np.ones(3, dtype=bool),
        quantile=0.10,
    )
    assert diagnostics.reference_standard_deviation == 0.0
    assert diagnostics.adaptive_target_defined is False


def test_stratified_random_spread_subsample_is_deterministic_and_bounded() -> None:
    rng = np.random.default_rng(103)
    increments = rng.normal(scale=8.0e-4, size=(1000, 4, 3))
    samples = np.mod(0.35 + np.cumsum(increments, axis=0), 1.0)
    kwargs = dict(
        weights=np.full(1000, 1.0 / 1000.0),
        cell=np.asarray(
            [[9.0, 0.0, 0.0], [2.0, 8.0, 0.0], [1.0, 1.5, 7.0]],
            dtype=float,
        ),
        pbc=np.ones(3, dtype=bool),
        quantile=0.10,
        sample_size=128,
        sample_seed=742,
        sampling_strategy="stratified_random",
    )
    first = periodic_item_spread_diagnostics(samples, **kwargs)
    second = periodic_item_spread_diagnostics(samples, **kwargs)
    np.testing.assert_array_equal(
        first.sampled_frame_indices, second.sampled_frame_indices
    )
    np.testing.assert_array_equal(first.standard_deviations, second.standard_deviations)
    assert first.source_frame_count == 1000
    assert first.sampled_frame_indices.size == 128
    assert first.sampling_strategy == "stratified_random"
    assert np.all(np.diff(first.sampled_frame_indices) > 0)
    metadata = first.metadata_dict()
    assert metadata["spread_source_frame_count"] == 1000
    assert metadata["spread_sampled_frame_count"] == 128
    assert metadata["spread_sampling_seed"] == 742


def test_stratified_random_spread_estimate_tracks_all_frame_reference() -> None:
    rng = np.random.default_rng(451)
    phase = np.linspace(0.0, 7.0 * np.pi, 800)
    base = np.column_stack(
        [
            0.48 + 0.012 * np.sin(phase),
            0.51 + 0.009 * np.cos(0.7 * phase),
            0.33 + 0.006 * np.sin(1.3 * phase),
        ]
    )
    samples = np.mod(
        base[:, None, :] + rng.normal(scale=8.0e-4, size=(800, 6, 3)), 1.0
    )
    common = dict(
        weights=np.full(800, 1.0 / 800.0),
        cell=np.eye(3) * 12.0,
        pbc=np.ones(3, dtype=bool),
        quantile=0.10,
    )
    exact = periodic_item_spread_diagnostics(
        samples,
        sample_size=800,
        sample_seed=0,
        sampling_strategy="all",
        **common,
    )
    sampled = periodic_item_spread_diagnostics(
        samples,
        sample_size=128,
        sample_seed=17,
        sampling_strategy="stratified_random",
        **common,
    )
    assert sampled.reference_standard_deviation == pytest.approx(
        exact.reference_standard_deviation, rel=0.025
    )
