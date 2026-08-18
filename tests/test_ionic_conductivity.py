"""Focused C2 tests for ionic conductivity and Nernst-Einstein comparison."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from scipy.constants import Boltzmann, elementary_charge

import mdstats
from mdstats import (
    AtomisticFrameCollection,
    CurrentCorrelationResult,
    DiffusionEstimate,
    FrameCollectionProvenance,
    FrameSemantics,
    IonicConductivityEstimate,
    IonicConductivityResult,
    NernstEinsteinComparisonResult,
    compute_charge_current,
    compute_nernst_einstein_comparison,
    estimate_ionic_conductivity_plateau,
    integrate_ionic_conductivity,
)
from mdstats.analysis._dynamics_common import resolve_analysis_subspace


def make_collection(
    *,
    n_frames: int = 8,
    dt: float = 0.5,
    cells: np.ndarray | None = None,
    pbc: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    if atomic_numbers is None:
        atomic_numbers = np.array([11, 17], dtype=np.int32)
    n_atoms = int(atomic_numbers.size)
    if cells is None:
        cells = np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0)
    if pbc is None:
        pbc = np.ones(3, dtype=np.bool_)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=atomic_numbers,
        masses=np.arange(1, n_atoms + 1, dtype=np.float64),
        pbc=np.asarray(pbc, dtype=np.bool_),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64) * dt,
        cells=np.asarray(cells, dtype=np.float64),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        velocities=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("conductivity-synthetic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def make_correlation(
    scalar: np.ndarray,
    *,
    lag_steps: np.ndarray | None = None,
    groups: bool = False,
    collection: AtomisticFrameCollection | None = None,
) -> CurrentCorrelationResult:
    scalar = np.asarray(scalar, dtype=np.float64)
    if lag_steps is None:
        lag_steps = np.arange(scalar.size, dtype=np.int64)
    lag_steps = np.asarray(lag_steps, dtype=np.int64)
    if collection is None:
        collection = make_collection(n_frames=max(8, int(lag_steps[-1]) + 2))
    current = compute_charge_current(
        collection,
        charges=[1.0, -1.0],
        species_groups=(
            {"cation": "Na", "anion": "Cl"}
            if groups
            else None
        ),
    )
    times = lag_steps.astype(np.float64) * current.sample_spacing_ps
    components = np.repeat((scalar / 3.0)[:, None], 3, axis=1)
    tensor = np.zeros((scalar.size, 3, 3), dtype=np.float64)
    tensor[:, 0, 0] = scalar / 3.0
    tensor[:, 1, 1] = scalar / 3.0
    tensor[:, 2, 2] = scalar / 3.0
    group_scalar = None
    group_tensor = None
    if groups:
        fractions = np.array([[0.40, 0.10], [0.20, 0.30]], dtype=np.float64)
        group_scalar = scalar[:, None, None] * fractions[None, :, :]
        group_tensor = np.zeros((scalar.size, 2, 2, 3, 3), dtype=np.float64)
        for axis in range(3):
            group_tensor[..., axis, axis] = group_scalar / 3.0
    return CurrentCorrelationResult(
        lag_steps=lag_steps,
        lag_times=times,
        scalar=scalar,
        components=components,
        tensor=tensor,
        group_names=current.group_names,
        group_scalar=group_scalar,
        group_tensor=group_tensor,
        n_origins=np.full(scalar.size, 2, dtype=np.int64),
        backend="direct",
        charges_e=current.charges_e,
        current_atom_indices=current.current_atom_indices,
        group_atom_indices=current.group_atom_indices,
        total_charge_e=current.total_charge_e,
        neutrality_tolerance_e=current.neutrality_tolerance_e,
        pbc=current.pbc,
        cell_volumes_a3=current.cell_volumes_a3,
        cell_mode=current.cell_mode,
        fixed_volume_a3=current.fixed_volume_a3,
        signature=current.signature,
        metadata={"contract_version": "test-current-correlation"},
    )


def make_diffusion(
    conductivity: IonicConductivityEstimate,
    name: str,
    value: float,
    *,
    fingerprint: str | None = None,
    drift_mode: str | None | object = ...,
    atom_indices: np.ndarray | None = None,
    dimensions: int = 3,
) -> DiffusionEstimate:
    group_indices = np.asarray(
        conductivity.group_atom_indices[name]
        if atom_indices is None
        else atom_indices,
        dtype=np.int64,
    )
    base = conductivity.signature
    if dimensions == 3:
        subspace = resolve_analysis_subspace()
    else:
        subspace = resolve_analysis_subspace(axes=("x",))
    kwargs = {
        "atom_indices": group_indices,
        "projection_basis": subspace.projection_basis,
        "projection_labels": subspace.labels,
        "coordinate_mode": "laboratory",
        "reference_cell_mode": None,
        "reference_cell": None,
    }
    if fingerprint is not None:
        kwargs["trajectory_fingerprint"] = fingerprint
    if drift_mode is not ...:
        kwargs["drift_mode"] = drift_mode
        kwargs["drift_atom_indices"] = (
            None if drift_mode is None else group_indices
        )
    signature = replace(base, **kwargs)
    return DiffusionEstimate(
        value_a2_per_ps=value,
        standard_error_a2_per_ps=None,
        time_range_ps=(1.0, 2.0),
        method="explicit",
        component=("scalar" if dimensions == 3 else "x"),
        dimensions=dimensions,
        n_points=4,
        is_stable=None,
        diagnostics={},
        metadata={},
        projection_basis=subspace.projection_basis,
        projection_labels=subspace.labels,
        signature=signature,
    )


def make_estimate_for_ne(
    *,
    collective: float,
    diffusion_values: tuple[float, float],
) -> tuple[IonicConductivityEstimate, dict[str, DiffusionEstimate]]:
    correlation = make_correlation(np.array([2.0, 0.0, 0.0, 0.0]), groups=True)
    running = integrate_ionic_conductivity(correlation, temperature_k=800.0)
    group_indices = running.group_atom_indices
    prefactor = elementary_charge**2 * 1.0e22 / (Boltzmann * 800.0 * 1000.0)
    contributions = np.array(diffusion_values) * prefactor
    group_pair = np.diag(contributions)
    scale = 0.0 if np.sum(group_pair) == 0.0 else collective / float(np.sum(group_pair))
    if np.sum(group_pair) == 0.0:
        group_pair = np.zeros((2, 2), dtype=np.float64)
    else:
        group_pair *= scale
    estimate = IonicConductivityEstimate(
        value_s_per_m=collective,
        standard_error_s_per_m=None,
        time_range_ps=(0.5, 1.5),
        method="explicit",
        n_points=3,
        is_stable=None,
        diagnostics={},
        group_names=running.group_names,
        group_pair_values_s_per_m=group_pair,
        temperature_k=running.temperature_k,
        volume_a3=running.volume_a3,
        pbc=running.pbc,
        cell_mode=running.cell_mode,
        fixed_volume_a3=running.fixed_volume_a3,
        total_charge_e=running.total_charge_e,
        neutrality_tolerance_e=running.neutrality_tolerance_e,
        charges_e=running.charges_e,
        current_atom_indices=running.current_atom_indices,
        group_atom_indices=group_indices,
        signature=running.signature,
        metadata={},
    )
    diffusions = {
        "cation": make_diffusion(estimate, "cation", diffusion_values[0]),
        "anion": make_diffusion(estimate, "anion", diffusion_values[1]),
    }
    return estimate, diffusions


def test_exact_si_conversion_and_cumulative_trapezoid() -> None:
    correlation = make_correlation(np.array([2.0, 2.0, 2.0]))
    result = integrate_ionic_conductivity(correlation, temperature_k=500.0)
    np.testing.assert_allclose(
        result.integrated_correlation_e2_a2_per_ps,
        [0.0, 1.0, 2.0],
    )
    expected_prefactor = elementary_charge**2 * 1.0e22 / (
        3.0 * Boltzmann * 500.0 * 1000.0
    )
    assert result.conductivity_prefactor == pytest.approx(expected_prefactor, rel=2e-15)
    np.testing.assert_allclose(
        result.running_conductivity_s_per_m,
        np.array([0.0, 1.0, 2.0]) * expected_prefactor,
    )
    assert result.metadata["conductivity_units"] == "S/m"


def test_inverse_temperature_and_volume_scaling() -> None:
    correlation = make_correlation(np.array([1.0, 1.0, 1.0]))
    baseline = integrate_ionic_conductivity(correlation, temperature_k=400.0)
    hot = integrate_ionic_conductivity(correlation, temperature_k=800.0)
    np.testing.assert_allclose(hot.running_conductivity_s_per_m, baseline.running_conductivity_s_per_m / 2.0)

    small_collection = make_collection(cells=np.repeat((np.eye(3) * 5.0)[None], 8, axis=0))
    small = integrate_ionic_conductivity(
        make_correlation(np.array([1.0, 1.0, 1.0]), collection=small_collection),
        temperature_k=400.0,
    )
    np.testing.assert_allclose(
        small.running_conductivity_s_per_m,
        baseline.running_conductivity_s_per_m * 8.0,
    )


def test_truncation_and_volume_assertion() -> None:
    correlation = make_correlation(np.ones(6))
    result = integrate_ionic_conductivity(
        correlation,
        temperature_k=600.0,
        volume_a3=1000.0,
        maximum_time_ps=1.0,
    )
    np.testing.assert_array_equal(result.lag_steps, [0, 1, 2])
    assert result.metadata["volume_argument_was_asserted"] is True
    with pytest.raises(ValueError, match="beyond"):
        integrate_ionic_conductivity(correlation, temperature_k=600.0, maximum_time_ps=99.0)
    with pytest.raises(ValueError, match="inconsistent"):
        integrate_ionic_conductivity(correlation, temperature_k=600.0, volume_a3=999.0)


def test_group_pair_integrals_remain_ordered_and_sum_to_total() -> None:
    correlation = make_correlation(np.array([2.0, 1.0, 0.5, 0.25]), groups=True)
    result = integrate_ionic_conductivity(correlation, temperature_k=700.0)
    assert result.group_running_conductivity_s_per_m.shape == (4, 2, 2)
    np.testing.assert_allclose(
        np.sum(result.group_running_conductivity_s_per_m, axis=(1, 2)),
        result.running_conductivity_s_per_m,
    )
    assert not np.allclose(
        result.group_running_conductivity_s_per_m[:, 0, 1],
        result.group_running_conductivity_s_per_m[:, 1, 0],
    )


def test_fixed_full_periodic_provenance_is_required() -> None:
    partial = make_collection(pbc=np.array([True, True, False]))
    with pytest.raises(ValueError, match="periodicity"):
        integrate_ionic_conductivity(
            make_correlation(np.ones(3), collection=partial),
            temperature_k=500.0,
        )
    cells = np.repeat(np.eye(3)[None] * 10.0, 8, axis=0)
    cells[1:, 0, 0] += 0.1
    variable = make_collection(cells=cells)
    with pytest.raises(ValueError, match="fixed full-cell-matrix"):
        integrate_ionic_conductivity(
            make_correlation(np.ones(3), collection=variable),
            temperature_k=500.0,
            volume_a3=1000.0,
        )


def test_plateau_estimate_and_group_pair_sum() -> None:
    correlation = make_correlation(np.array([2.0, 0.0, 0.0, 0.0, 0.0]), groups=True)
    running = integrate_ionic_conductivity(correlation, temperature_k=500.0)
    estimate = estimate_ionic_conductivity_plateau(
        running,
        time_range_ps=(0.5, 2.0),
        minimum_points=4,
        slope_tolerance_s_per_m_ps=1.0e-12,
    )
    assert estimate.value_s_per_m == pytest.approx(running.running_conductivity_s_per_m[1])
    assert estimate.is_stable is True
    assert estimate.diagnostics["linear_slope_s_per_m_ps"] == pytest.approx(0.0, abs=1e-15)
    assert np.sum(estimate.group_pair_values_s_per_m) == pytest.approx(estimate.value_s_per_m)


def test_plateau_validation_and_nonuniform_stored_grid() -> None:
    running = integrate_ionic_conductivity(
        make_correlation(np.ones(4), lag_steps=np.array([0, 1, 3, 4])),
        temperature_k=500.0,
    )
    with pytest.raises(ValueError, match="uniformly spaced"):
        estimate_ionic_conductivity_plateau(
            running,
            time_range_ps=(0.0, 2.0),
            minimum_points=4,
        )
    with pytest.raises(ValueError, match="minimum_points"):
        estimate_ionic_conductivity_plateau(
            running,
            time_range_ps=(0.0, 0.5),
            minimum_points=3,
        )
    with pytest.raises(TypeError, match="minimum_points"):
        estimate_ionic_conductivity_plateau(
            running,
            time_range_ps=(0.0, 0.5),
            minimum_points=True,
        )


def test_nernst_einstein_independent_limit_and_species_contributions() -> None:
    estimate, diffusions = make_estimate_for_ne(collective=1.0, diffusion_values=(0.3, 0.7))
    prefactor = elementary_charge**2 * 1.0e22 / (Boltzmann * 800.0 * 1000.0)
    expected_ne = prefactor * 1.0
    estimate = replace(
        estimate,
        value_s_per_m=expected_ne,
        group_pair_values_s_per_m=np.diag([0.3 * prefactor, 0.7 * prefactor]),
    )
    result = compute_nernst_einstein_comparison(estimate, diffusions)
    assert result.collective_conductivity_s_per_m == pytest.approx(expected_ne)
    assert result.nernst_einstein_conductivity_s_per_m == pytest.approx(expected_ne)
    assert result.signed_difference_s_per_m == pytest.approx(0.0, abs=5e-14)
    np.testing.assert_allclose(result.species_contributions_s_per_m, [0.3 * prefactor, 0.7 * prefactor])
    np.testing.assert_array_equal(result.species_counts, [1, 1])
    np.testing.assert_allclose(result.group_charges_e, [1.0, -1.0])


def test_collective_enhancement_suppression_and_directional_ratios() -> None:
    estimate, diffusions = make_estimate_for_ne(collective=2.0, diffusion_values=(0.2, 0.2))
    ne = compute_nernst_einstein_comparison(estimate, diffusions).nernst_einstein_conductivity_s_per_m
    enhanced = replace(
        estimate,
        value_s_per_m=2.0 * ne,
        group_pair_values_s_per_m=np.array([[ne, 0.25 * ne], [0.25 * ne, 0.5 * ne]]),
    )
    result = compute_nernst_einstein_comparison(enhanced, diffusions)
    assert result.collective_over_nernst_einstein == pytest.approx(2.0)
    assert result.nernst_einstein_over_collective == pytest.approx(0.5)
    assert result.off_diagonal_group_contribution_s_per_m == pytest.approx(0.5 * ne)

    suppressed = replace(
        estimate,
        value_s_per_m=0.5 * ne,
        group_pair_values_s_per_m=np.diag([0.25 * ne, 0.25 * ne]),
    )
    result2 = compute_nernst_einstein_comparison(suppressed, diffusions)
    assert result2.signed_difference_s_per_m == pytest.approx(-0.5 * ne)


def test_zero_denominator_ratio_policy() -> None:
    estimate, diffusions = make_estimate_for_ne(collective=0.0, diffusion_values=(0.0, 0.0))
    result = compute_nernst_einstein_comparison(estimate, diffusions)
    assert np.isnan(result.collective_over_nernst_einstein)
    assert np.isnan(result.nernst_einstein_over_collective)
    assert result.collective_over_nernst_einstein_defined is False
    assert result.nernst_einstein_over_collective_defined is False


def test_nernst_einstein_rejects_keys_selection_rank_and_trajectory_mismatch() -> None:
    estimate, diffusions = make_estimate_for_ne(collective=1.0, diffusion_values=(0.1, 0.2))
    with pytest.raises(ValueError, match="keys and order"):
        compute_nernst_einstein_comparison(estimate, {"anion": diffusions["anion"], "cation": diffusions["cation"]})
    wrong_selection = dict(diffusions)
    wrong_selection["cation"] = make_diffusion(
        estimate,
        "cation",
        0.1,
        atom_indices=np.array([1]),
    )
    with pytest.raises(ValueError, match="atom selection"):
        compute_nernst_einstein_comparison(estimate, wrong_selection)
    wrong_rank = dict(diffusions)
    wrong_rank["cation"] = make_diffusion(estimate, "cation", 0.1, dimensions=1)
    with pytest.raises(ValueError, match="three-dimensional"):
        compute_nernst_einstein_comparison(estimate, wrong_rank)
    wrong_trajectory = dict(diffusions)
    wrong_trajectory["cation"] = make_diffusion(
        estimate,
        "cation",
        0.1,
        fingerprint="different",
    )
    with pytest.raises(ValueError, match="trajectory_fingerprint"):
        compute_nernst_einstein_comparison(estimate, wrong_trajectory)


def test_nernst_einstein_rejects_mixed_charge_negative_diffusion_and_state_mismatch() -> None:
    estimate, diffusions = make_estimate_for_ne(collective=1.0, diffusion_values=(0.1, 0.2))
    with pytest.raises(ValueError, match="nonnegative"):
        bad = dict(diffusions)
        bad["cation"] = make_diffusion(estimate, "cation", -0.1)
        compute_nernst_einstein_comparison(estimate, bad)

    with pytest.raises(ValueError, match="temperature"):
        compute_nernst_einstein_comparison(estimate, diffusions, temperature_k=900.0)
    with pytest.raises(ValueError, match="volume"):
        compute_nernst_einstein_comparison(estimate, diffusions, volume_a3=999.0)

    mixed = replace(
        estimate,
        group_names=("mixed",),
        group_atom_indices={"mixed": np.array([0, 1], dtype=np.int64)},
        group_pair_values_s_per_m=np.array([[estimate.value_s_per_m]]),
    )
    mixed_diffusion = {"mixed": make_diffusion(mixed, "mixed", 0.1)}
    with pytest.raises(ValueError, match="uniform nonzero charge"):
        compute_nernst_einstein_comparison(mixed, mixed_diffusion)


def test_result_constructor_invariants_fail_closed() -> None:
    result = integrate_ionic_conductivity(
        make_correlation(np.array([1.0, 1.0, 1.0]), groups=True),
        temperature_k=500.0,
    )
    broken = np.array(result.running_conductivity_s_per_m, copy=True)
    broken[-1] += 1.0
    with pytest.raises(ValueError, match="SI conversion"):
        replace(result, running_conductivity_s_per_m=broken)
    broken_group = np.array(result.group_running_conductivity_s_per_m, copy=True)
    broken_group[-1, 0, 0] += 1.0
    with pytest.raises(ValueError, match="SI conversion"):
        replace(result, group_running_conductivity_s_per_m=broken_group)
    broken_integral = np.array(
        result.group_integrated_correlation_e2_a2_per_ps,
        copy=True,
    )
    broken_integral[-1, 0, 0] += 1.0
    broken_integral[-1, 1, 1] -= 1.0
    with pytest.raises(ValueError, match="quadrature"):
        replace(
            result,
            group_integrated_correlation_e2_a2_per_ps=broken_integral,
            group_running_conductivity_s_per_m=(
                broken_integral * result.conductivity_prefactor
            ),
        )


def test_deep_immutability_and_public_exports() -> None:
    running = integrate_ionic_conductivity(
        make_correlation(np.array([2.0, 0.0, 0.0, 0.0]), groups=True),
        temperature_k=800.0,
    )
    estimate = estimate_ionic_conductivity_plateau(
        running,
        time_range_ps=(0.5, 1.5),
        minimum_points=3,
    )
    diffusions = {
        name: make_diffusion(estimate, name, 0.1)
        for name in estimate.group_names
    }
    comparison = compute_nernst_einstein_comparison(estimate, diffusions)
    assert isinstance(running, IonicConductivityResult)
    assert isinstance(estimate, IonicConductivityEstimate)
    assert isinstance(comparison, NernstEinsteinComparisonResult)
    assert mdstats.integrate_ionic_conductivity is integrate_ionic_conductivity
    assert "IonicConductivityResult" in mdstats.__all__
    assert "compute_nernst_einstein_comparison" in mdstats.__all__
    with pytest.raises(ValueError):
        running.running_conductivity_s_per_m[0] = 1.0
    with pytest.raises(ValueError):
        estimate.group_pair_values_s_per_m[0, 0] = 1.0
    with pytest.raises(TypeError):
        comparison.metadata["new"] = 1  # type: ignore[index]
