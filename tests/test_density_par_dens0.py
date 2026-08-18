"""PAR-DENS0 basin-aware spread and convergence qualification."""

from __future__ import annotations

import numpy as np
import pytest

import mdstats.analysis.density.diagnostics as diagnostics_module
from mdstats import periodic_item_spread_diagnostics


def _fractional_gaussian(
    centers_cartesian: np.ndarray,
    *,
    frames: int,
    sigma: float,
    cell_length: float = 20.0,
    seed: int = 7,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centers = np.asarray(centers_cartesian, dtype=float)
    noise = rng.normal(0.0, sigma, size=(frames, centers.shape[0], 3))
    return (centers[None, :, :] + noise) / cell_length


def test_provided_two_basin_labels_remove_transition_displacement() -> None:
    frames = 2000
    cell = np.eye(3) * 20.0
    rng = np.random.default_rng(11)
    cart = rng.normal(0.0, 0.08, size=(frames, 1, 3))
    cart[:990, 0, :] += np.array([5.0, 5.0, 5.0])
    cart[1010:, 0, :] += np.array([6.2, 5.0, 5.0])
    cart[990:1010, 0, :] += np.linspace(
        np.array([5.0, 5.0, 5.0]), np.array([6.2, 5.0, 5.0]), 20
    )
    samples = cart / 20.0
    weights = np.ones(frames)

    global_spread = periodic_item_spread_diagnostics(
        samples,
        weights=weights,
        quantile=0.1,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
        sampling_strategy="all",
        basin_mode="global",
    )
    labels = np.full((frames, 1), -1, dtype=np.int64)
    labels[:990, 0] = 0
    labels[1010:, 0] = 1
    basin_spread = periodic_item_spread_diagnostics(
        samples,
        weights=weights,
        quantile=0.1,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
        sampling_strategy="all",
        basin_labels_by_frame=labels,
        basin_label_source="test-residences",
    )

    assert global_spread.standard_deviations[0] > 0.30
    assert basin_spread.standard_deviations[0] == pytest.approx(0.08, abs=0.006)
    assert basin_spread.standard_deviations[0] < 0.35 * global_spread.standard_deviations[0]
    assert basin_spread.basin_counts_by_item.tolist() == [2]
    assert basin_spread.excluded_source_sample_counts_by_item.tolist() == [20]
    assert basin_spread.basin_source == "test-residences"


def test_auto_prepass_does_not_split_compact_single_basin() -> None:
    frames = 4096
    cell = np.eye(3) * 20.0
    t = np.linspace(0.0, 24.0 * np.pi, frames, endpoint=False)
    cart = np.empty((frames, 1, 3), dtype=float)
    cart[:, 0, 0] = 5.0 + 0.08 * np.sin(t)
    cart[:, 0, 1] = 6.0 + 0.06 * np.cos(0.7 * t)
    cart[:, 0, 2] = 7.0 + 0.05 * np.sin(1.3 * t)

    global_spread = periodic_item_spread_diagnostics(
        cart / 20.0,
        weights=np.ones(frames),
        quantile=0.1,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
        sampling_strategy="all",
        basin_mode="global",
    )
    auto_spread = periodic_item_spread_diagnostics(
        cart / 20.0,
        weights=np.ones(frames),
        quantile=0.1,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
        sampling_strategy="all",
        basin_mode="auto",
    )

    assert auto_spread.basin_counts_by_item.tolist() == [1]
    assert auto_spread.excluded_source_sample_counts_by_item.tolist() == [0]
    assert auto_spread.standard_deviations[0] == pytest.approx(
        global_spread.standard_deviations[0], rel=2.0e-12
    )


def test_compact_all_frame_path_does_not_require_quadratic_medoid(monkeypatch: pytest.MonkeyPatch) -> None:
    frames = 5000
    cell = np.eye(3) * 20.0
    samples = _fractional_gaussian(
        np.array([[5.0, 6.0, 7.0]]), frames=frames, sigma=0.08, seed=19
    )

    def forbidden_medoid(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("quadratic medoid fallback should not run for a compact basin")

    monkeypatch.setattr(diagnostics_module, "_weighted_medoid_index", forbidden_medoid)
    result = periodic_item_spread_diagnostics(
        samples,
        weights=np.ones(frames),
        quantile=0.1,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
        sampling_strategy="all",
        basin_mode="global",
    )

    assert result.standard_deviations[0] == pytest.approx(0.08, abs=0.004)
    assert result.basin_diagnostics[0].compact_fast_path_count == 1
    assert result.basin_diagnostics[0].fallback_mean_count == 0


def test_production_replicates_use_convergence_anchor_and_report_uncertainty() -> None:
    frames = 10001
    cell = np.eye(3) * 20.0
    t = np.arange(frames, dtype=float)
    # Multiple incommensurate oscillations make systematic undersampling visible,
    # while the deterministic midpoint anchor remains reproducible.
    cart = np.empty((frames, 8, 3), dtype=float)
    for item in range(8):
        phase = 0.37 * item
        cart[:, item, 0] = 5.0 + item * 0.2 + 0.10 * np.sin(0.017 * t + phase)
        cart[:, item, 1] = 6.0 + 0.08 * np.cos(0.023 * t + 0.5 * phase)
        cart[:, item, 2] = 7.0 + 0.06 * np.sin(0.031 * t - phase)
    samples = cart / 20.0
    weights = np.ones(frames)

    exact = periodic_item_spread_diagnostics(
        samples,
        weights=weights,
        quantile=0.1,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
        sampling_strategy="all",
        basin_mode="global",
    )
    production = periodic_item_spread_diagnostics(
        samples,
        weights=weights,
        quantile=0.1,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
        sample_size=128,
        sample_seed=0,
        sampling_strategy="stratified_random",
        replicate_count=4,
        max_replicate_count=8,
        convergence_relative_tolerance=0.01,
        basin_mode="global",
    )

    assert production.reference_standard_deviation == pytest.approx(
        exact.reference_standard_deviation, rel=0.01
    )
    convergence = production.convergence
    assert convergence is not None
    assert convergence.effective_sample_count >= 512
    assert convergence.realized_replicate_count in {4, 8}
    assert convergence.replicate_reference_standard_deviations.size == convergence.realized_replicate_count
    assert convergence.progressive_reference_standard_deviations.size >= 2
    assert convergence.reference_standard_error is not None
    assert convergence.confidence_interval_low is not None
    assert convergence.confidence_interval_high is not None
    assert convergence.converged is True
    assert production.sampling_strategy == "convergence_qualified_stratified"


def test_final_segmentation_adapter_excludes_retained_excursion_membership() -> None:
    from mdstats.analysis.density.diagnostics import (
        spread_basin_labels_from_final_segmentation,
    )
    from mdstats.analysis.density.final_segmentation import FinalPassageOutcome
    from mdstats.analysis.density import FinalSegmentationOptions
    from tests.test_stage11e6_final_segmentation import _final
    from tests.test_stage11e4_temporal_assignment import _jitter

    xs = np.r_[_jitter(0.2, 8), [0.45], _jitter(0.2, 8)]
    catalog, _temporal, result = _final(
        xs,
        options=FinalSegmentationOptions(
            minimum_core_entry_frames=2,
            minimum_basin_exit_frames=2,
            recrossing_window_frames=4,
            sensitivity_thresholds=((2, 2),),
            sensitivity_stride_factors=(1,),
            minimum_events_for_stability=1,
        ),
    )
    labels = spread_basin_labels_from_final_segmentation(catalog, result)
    retained = next(
        passage for passage in result.passages
        if passage.outcome is FinalPassageOutcome.RETAINED_EXCURSION
    )
    retained_frames = set(int(catalog.frame_indices[i]) for i in retained.sample_indices)
    frame_axis = np.asarray(catalog.temporal_weighting.frame_indices, dtype=np.int64)
    positions = [i for i, frame in enumerate(frame_axis) if int(frame) in retained_frames]

    assert labels.shape == (frame_axis.size, 1)
    assert positions
    assert np.all(labels[positions, 0] == -1)
    assert np.any(labels[:, 0] == 0)
