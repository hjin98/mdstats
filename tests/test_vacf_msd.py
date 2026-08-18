"""Tests for VACF-to-MSD reconstruction consistency diagnostics."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_msd,
    compute_vacf,
    reconstruct_msd_from_vacf,
)
from mdstats.analysis.vacf import VACFResult
from mdstats.analysis.vacf_transport import VACFMSDResult


def make_vacf(
    components_per_particle: np.ndarray,
    lag_times: np.ndarray,
    *,
    n_atoms: int = 2,
    weighting: str = "uniform",
    atom_weights: np.ndarray | None = None,
) -> VACFResult:
    components_per_particle = np.asarray(components_per_particle, dtype=np.float64)
    lag_times = np.asarray(lag_times, dtype=np.float64)
    n_lags = lag_times.size
    if atom_weights is None:
        if weighting == "mass":
            atom_weights = np.full(n_atoms, 10.0, dtype=np.float64)
        else:
            atom_weights = np.ones(n_atoms, dtype=np.float64)
    atom_weights = np.asarray(atom_weights, dtype=np.float64)
    weight_sum = float(np.sum(atom_weights))

    components_sum = components_per_particle * weight_sum
    scalar_sum = np.sum(components_sum, axis=1)
    tensor = np.zeros((n_lags, 3, 3), dtype=np.float64)
    diagonal = np.arange(3)
    tensor[:, diagonal, diagonal] = components_sum

    return VACFResult(
        lag_steps=np.arange(n_lags, dtype=np.int64),
        lag_times=lag_times,
        scalar_sum=scalar_sum,
        components_sum=components_sum,
        tensor_sum=tensor,
        per_atom_scalar=None,
        per_atom_components=None,
        per_atom_indices=None,
        n_origins=np.arange(n_lags, 0, -1, dtype=np.int64),
        atom_indices=np.arange(n_atoms, dtype=np.int64),
        atom_weights=atom_weights,
        weight_sum=weight_sum,
        weighting=weighting,
        drift_mode=None,
        backend="direct",
        metadata={"source_files": ["synthetic"]},
    )


def make_ballistic_collection(
    velocity: np.ndarray,
    *,
    n_frames: int = 24,
    dt_ps: float = 0.05,
) -> AtomisticFrameCollection:
    velocity = np.asarray(velocity, dtype=np.float64)
    times = np.arange(n_frames, dtype=np.float64) * dt_ps
    velocities = np.repeat(velocity[None, None, :], n_frames, axis=0)
    cartesian = times[:, None, None] * velocity[None, None, :]
    cell = np.eye(3, dtype=np.float64) * 100.0
    cells = np.repeat(cell[None, :, :], n_frames, axis=0)
    fractional = np.einsum("tni,ij->tnj", cartesian, np.linalg.inv(cell))
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.array([1], dtype=np.int32),
        masses=np.array([1.0], dtype=np.float64),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames, dtype=np.int64),
        times=times,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=velocities,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("ballistic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_constant_vacf_reconstructs_exact_ballistic_msd() -> None:
    times = np.linspace(0.0, 2.0, 17)
    components = np.repeat(np.array([[1.0, 4.0, 9.0]]), times.size, axis=0)
    vacf = make_vacf(components, times, n_atoms=7)

    scalar = reconstruct_msd_from_vacf(vacf)
    x = reconstruct_msd_from_vacf(vacf, component="x")

    assert isinstance(scalar, VACFMSDResult)
    np.testing.assert_allclose(scalar.reconstructed_msd_a2, 14.0 * times**2)
    np.testing.assert_allclose(x.reconstructed_msd_a2, times**2)
    np.testing.assert_allclose(scalar.cumulative_vacf_a2_per_ps, 14.0 * times)
    np.testing.assert_allclose(
        scalar.cumulative_time_weighted_vacf_a2,
        7.0 * times**2,
    )
    assert scalar.metadata["direct_position_msd_is_primary"] is True


def test_exponential_vacf_agrees_with_analytic_msd_on_fine_grid() -> None:
    times = np.linspace(0.0, 6.0, 12001)
    amplitude = 2.5
    tau = 0.7
    correlation = amplitude * np.exp(-times / tau)
    components = np.zeros((times.size, 3), dtype=np.float64)
    components[:, 1] = correlation
    vacf = make_vacf(components, times, n_atoms=1)

    result = reconstruct_msd_from_vacf(vacf, component="y")
    expected = 2.0 * amplitude * (
        tau * times - tau**2 * (1.0 - np.exp(-times / tau))
    )

    np.testing.assert_allclose(result.reconstructed_msd_a2, expected, rtol=5e-7, atol=5e-7)


def test_nonuniform_grid_matches_direct_sampled_nested_kernel() -> None:
    times = np.array([0.0, 0.12, 0.41, 0.93, 1.8], dtype=np.float64)
    components = np.zeros((times.size, 3), dtype=np.float64)
    components[:, 2] = [3.0, 2.4, 1.1, -0.2, -0.5]
    vacf = make_vacf(components, times)

    result = reconstruct_msd_from_vacf(vacf, component="z")
    i0 = np.zeros(times.size)
    i1 = np.zeros(times.size)
    for index in range(1, times.size):
        dt = times[index] - times[index - 1]
        c0 = components[index - 1, 2]
        c1 = components[index, 2]
        i0[index] = i0[index - 1] + 0.5 * dt * (c0 + c1)
        i1[index] = i1[index - 1] + 0.5 * dt * (
            times[index - 1] * c0 + times[index] * c1
        )
    expected = 2.0 * (times * i0 - i1)

    np.testing.assert_allclose(result.cumulative_vacf_a2_per_ps, i0)
    np.testing.assert_allclose(result.cumulative_time_weighted_vacf_a2, i1)
    np.testing.assert_allclose(result.reconstructed_msd_a2, expected)


def test_scalar_reconstruction_equals_sum_of_cartesian_reconstructions() -> None:
    times = np.linspace(0.0, 2.0, 101)
    components = np.column_stack(
        [
            np.exp(-times),
            2.0 * np.exp(-2.0 * times),
            0.25 * np.cos(0.7 * times),
        ]
    )
    vacf = make_vacf(components, times, n_atoms=4)

    scalar = reconstruct_msd_from_vacf(vacf)
    directional = [
        reconstruct_msd_from_vacf(vacf, component=axis)
        for axis in ("x", "y", "z")
    ]
    np.testing.assert_allclose(
        scalar.reconstructed_msd_a2,
        sum(result.reconstructed_msd_a2 for result in directional),
    )


def test_direct_ballistic_msd_matches_vacf_reconstruction() -> None:
    velocity = np.array([0.8, -0.35, 0.2], dtype=np.float64)
    collection = make_ballistic_collection(velocity)
    vacf = compute_vacf(collection, max_lag=10, backend="direct")
    direct_msd = compute_msd(collection, max_lag=10, backend="direct")
    reconstructed = reconstruct_msd_from_vacf(vacf)

    np.testing.assert_allclose(
        reconstructed.lag_times,
        direct_msd.lag_times,
    )
    np.testing.assert_allclose(
        reconstructed.reconstructed_msd_a2,
        direct_msd.msd,
        rtol=2e-13,
        atol=2e-14,
    )


def test_equal_explicit_weights_are_accepted_and_nonphysical_weights_rejected() -> None:
    times = np.linspace(0.0, 1.0, 5)
    components = np.ones((times.size, 3), dtype=np.float64)
    equal = make_vacf(
        components,
        times,
        n_atoms=3,
        weighting="explicit",
        atom_weights=np.array([2.5, 2.5, 2.5]),
    )
    assert reconstruct_msd_from_vacf(equal).weighting == "explicit_uniform"

    mass = make_vacf(components, times, weighting="mass")
    with pytest.raises(ValueError, match="mass-weighted"):
        reconstruct_msd_from_vacf(mass)

    nonuniform = make_vacf(
        components,
        times,
        n_atoms=3,
        weighting="explicit",
        atom_weights=np.array([1.0, 2.0, 1.0]),
    )
    with pytest.raises(ValueError, match="nonuniform"):
        reconstruct_msd_from_vacf(nonuniform)


def test_maximum_time_selects_existing_boundary_and_zero_is_valid() -> None:
    times = np.array([0.0, 0.2, 0.4, 0.6, 0.8])
    vacf = make_vacf(np.ones((times.size, 3)), times)

    truncated = reconstruct_msd_from_vacf(vacf, maximum_time_ps=0.51)
    np.testing.assert_array_equal(truncated.lag_times, [0.0, 0.2, 0.4])
    assert truncated.metadata["actual_maximum_time_ps"] == pytest.approx(0.4)

    zero = reconstruct_msd_from_vacf(vacf, maximum_time_ps=0.0)
    np.testing.assert_array_equal(zero.lag_times, [0.0])
    np.testing.assert_array_equal(zero.reconstructed_msd_a2, [0.0])


def test_input_vacf_is_not_mutated() -> None:
    times = np.linspace(0.0, 1.0, 9)
    vacf = make_vacf(np.arange(27, dtype=np.float64).reshape(9, 3), times)
    scalar_before = vacf.scalar_sum.copy()
    components_before = vacf.components_sum.copy()

    reconstruct_msd_from_vacf(vacf, component="x")

    np.testing.assert_array_equal(vacf.scalar_sum, scalar_before)
    np.testing.assert_array_equal(vacf.components_sum, components_before)


def test_option_validation() -> None:
    times = np.array([0.0, 0.5, 1.0])
    vacf = make_vacf(np.ones((3, 3)), times)

    with pytest.raises(TypeError, match="VACFResult"):
        reconstruct_msd_from_vacf(object())
    with pytest.raises(ValueError, match="component"):
        reconstruct_msd_from_vacf(vacf, component="xy")
    with pytest.raises(ValueError, match="integration"):
        reconstruct_msd_from_vacf(vacf, integration="simpson")
    with pytest.raises(TypeError, match="maximum_time_ps"):
        reconstruct_msd_from_vacf(vacf, maximum_time_ps="1.0")
    with pytest.raises(ValueError, match="finite and nonnegative"):
        reconstruct_msd_from_vacf(vacf, maximum_time_ps=-1.0)


def test_result_rejects_inconsistent_moment_or_msd_identity() -> None:
    times = np.array([0.0, 1.0])
    physical_vacf = np.array([1.0, 1.0])
    with pytest.raises(ValueError, match="cumulative_vacf"):
        VACFMSDResult(
            lag_times=times,
            reconstructed_msd_a2=np.array([0.0, 1.0]),
            physical_vacf_a2_per_ps2=physical_vacf,
            cumulative_vacf_a2_per_ps=np.array([0.0, 99.0]),
            cumulative_time_weighted_vacf_a2=np.array([0.0, 0.5]),
            component="x",
            weighting="uniform",
            integration="trapezoid",
        )

    with pytest.raises(ValueError, match="reconstructed_msd"):
        VACFMSDResult(
            lag_times=times,
            reconstructed_msd_a2=np.array([0.0, 99.0]),
            physical_vacf_a2_per_ps2=physical_vacf,
            cumulative_vacf_a2_per_ps=np.array([0.0, 1.0]),
            cumulative_time_weighted_vacf_a2=np.array([0.0, 0.5]),
            component="x",
            weighting="uniform",
            integration="trapezoid",
        )


def test_top_level_public_exports() -> None:
    import mdstats
    import mdstats.analysis as analysis

    assert mdstats.VACFMSDResult is VACFMSDResult
    assert analysis.VACFMSDResult is VACFMSDResult
    assert mdstats.reconstruct_msd_from_vacf is reconstruct_msd_from_vacf
    assert analysis.reconstruct_msd_from_vacf is reconstruct_msd_from_vacf
