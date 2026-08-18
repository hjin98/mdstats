from __future__ import annotations

import numpy as np
import pytest

from mdstats.analysis.vacf import VACFResult
from mdstats.analysis.vacf_transport import (
    VACFDiffusionResult,
    integrate_vacf_to_diffusion,
)


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
        metadata={
            "correlation_units": (
                "amu*Å^2/ps^2" if weighting == "mass" else "Å^2/ps^2"
            ),
            "source_files": ["synthetic"],
        },
    )


def test_constant_isotropic_vacf_produces_linear_running_diffusion() -> None:
    times = np.linspace(0.0, 2.0, 9)
    components = np.ones((times.size, 3), dtype=np.float64)
    vacf = make_vacf(components, times, n_atoms=7)

    result = integrate_vacf_to_diffusion(vacf)

    assert isinstance(result, VACFDiffusionResult)
    np.testing.assert_allclose(result.integrand, 1.0)
    np.testing.assert_allclose(result.running_diffusion_a2_per_ps, times)
    np.testing.assert_allclose(result.running_diffusion_cm2_per_s, times * 1.0e-4)
    assert result.metadata["plateau_selected"] is False
    assert result.metadata["last_value_is_not_automatically_converged"] is True


def test_exponential_vacf_agrees_with_analytic_integral_on_fine_grid() -> None:
    times = np.linspace(0.0, 5.0, 5001)
    tau = 0.8
    amplitude = 2.5
    correlation = amplitude * np.exp(-times / tau)
    components = np.zeros((times.size, 3), dtype=np.float64)
    components[:, 0] = correlation
    vacf = make_vacf(components, times, n_atoms=1)

    result = integrate_vacf_to_diffusion(vacf, component="x")
    expected = amplitude * tau * (1.0 - np.exp(-times / tau))

    np.testing.assert_allclose(
        result.running_diffusion_a2_per_ps,
        expected,
        rtol=3.0e-7,
        atol=3.0e-7,
    )


def test_nonuniform_grid_uses_sampled_trapezoids() -> None:
    times = np.array([0.0, 0.1, 0.4, 0.9, 1.7], dtype=np.float64)
    components = np.zeros((times.size, 3), dtype=np.float64)
    components[:, 2] = [2.0, 1.8, 1.0, 0.2, -0.1]
    vacf = make_vacf(components, times)

    result = integrate_vacf_to_diffusion(vacf, component="z")
    expected = np.zeros(times.size)
    for i in range(1, times.size):
        dt = times[i] - times[i - 1]
        expected[i] = expected[i - 1] + 0.5 * dt * (
            components[i - 1, 2] + components[i, 2]
        )

    np.testing.assert_allclose(result.running_diffusion_a2_per_ps, expected)


def test_component_integrals_reproduce_scalar_dimension_average() -> None:
    times = np.linspace(0.0, 1.0, 21)
    components = np.column_stack(
        [
            np.exp(-times),
            2.0 * np.exp(-2.0 * times),
            0.5 * np.cos(times),
        ]
    )
    vacf = make_vacf(components, times, n_atoms=4)

    scalar = integrate_vacf_to_diffusion(vacf, dimensions=3, component="scalar")
    directional = [
        integrate_vacf_to_diffusion(vacf, component=axis)
        for axis in ("x", "y", "z")
    ]

    reconstructed = sum(
        result.running_diffusion_a2_per_ps for result in directional
    ) / 3.0
    np.testing.assert_allclose(scalar.running_diffusion_a2_per_ps, reconstructed)


def test_normalization_is_independent_of_atom_count() -> None:
    times = np.linspace(0.0, 1.0, 11)
    components = np.zeros((times.size, 3), dtype=np.float64)
    components[:, 0] = 1.25

    one = integrate_vacf_to_diffusion(
        make_vacf(components, times, n_atoms=1), component="x"
    )
    many = integrate_vacf_to_diffusion(
        make_vacf(components, times, n_atoms=9), component="x"
    )

    np.testing.assert_allclose(
        one.running_diffusion_a2_per_ps,
        many.running_diffusion_a2_per_ps,
    )


def test_equal_explicit_weights_are_accepted_but_nonuniform_are_rejected() -> None:
    times = np.linspace(0.0, 1.0, 5)
    components = np.ones((times.size, 3), dtype=np.float64)

    equal = make_vacf(
        components,
        times,
        weighting="explicit",
        atom_weights=np.array([2.5, 2.5, 2.5]),
        n_atoms=3,
    )
    result = integrate_vacf_to_diffusion(equal)
    assert result.weighting == "explicit_uniform"

    nonuniform = make_vacf(
        components,
        times,
        weighting="explicit",
        atom_weights=np.array([1.0, 2.0, 1.0]),
        n_atoms=3,
    )
    with pytest.raises(ValueError, match="nonuniform"):
        integrate_vacf_to_diffusion(nonuniform)



def test_malformed_uniform_label_is_rejected() -> None:
    times = np.linspace(0.0, 1.0, 5)
    components = np.ones((times.size, 3), dtype=np.float64)
    malformed = make_vacf(
        components,
        times,
        weighting="uniform",
        atom_weights=np.array([1.0, 2.0]),
        n_atoms=2,
    )

    with pytest.raises(ValueError, match="labelled 'uniform'"):
        integrate_vacf_to_diffusion(malformed)

def test_mass_weighting_is_rejected_even_for_equal_masses() -> None:
    times = np.linspace(0.0, 1.0, 5)
    components = np.ones((times.size, 3), dtype=np.float64)
    mass_weighted = make_vacf(components, times, weighting="mass")

    with pytest.raises(ValueError, match="mass-weighted"):
        integrate_vacf_to_diffusion(mass_weighted)


def test_maximum_time_uses_largest_existing_lag_without_interpolation() -> None:
    times = np.array([0.0, 0.2, 0.4, 0.6, 0.8])
    components = np.ones((times.size, 3), dtype=np.float64)
    vacf = make_vacf(components, times)

    result = integrate_vacf_to_diffusion(vacf, maximum_time_ps=0.51)

    np.testing.assert_array_equal(result.lag_times, [0.0, 0.2, 0.4])
    assert result.metadata["requested_maximum_time_ps"] == pytest.approx(0.51)
    assert result.metadata["actual_maximum_time_ps"] == pytest.approx(0.4)
    assert result.metadata["source_lag_steps"] == (0, 1, 2)


def test_zero_time_truncation_returns_single_zero_sample() -> None:
    times = np.array([0.0, 0.5, 1.0])
    components = np.ones((times.size, 3), dtype=np.float64)
    vacf = make_vacf(components, times)

    result = integrate_vacf_to_diffusion(vacf, maximum_time_ps=0.0)

    np.testing.assert_array_equal(result.lag_times, [0.0])
    np.testing.assert_array_equal(result.running_diffusion_a2_per_ps, [0.0])


def test_input_arrays_are_not_mutated() -> None:
    times = np.linspace(0.0, 1.0, 6)
    components = np.arange(18, dtype=np.float64).reshape(6, 3)
    vacf = make_vacf(components, times)
    scalar_before = vacf.scalar_sum.copy()
    components_before = vacf.components_sum.copy()

    integrate_vacf_to_diffusion(vacf)

    np.testing.assert_array_equal(vacf.scalar_sum, scalar_before)
    np.testing.assert_array_equal(vacf.components_sum, components_before)


def test_option_validation() -> None:
    times = np.array([0.0, 0.5, 1.0])
    vacf = make_vacf(np.ones((3, 3)), times)

    with pytest.raises(TypeError, match="VACFResult"):
        integrate_vacf_to_diffusion(object())
    with pytest.raises(TypeError, match="dimensions"):
        integrate_vacf_to_diffusion(vacf, dimensions=True)
    with pytest.raises(ValueError, match="1, 2, or 3"):
        integrate_vacf_to_diffusion(vacf, dimensions=4)
    with pytest.raises(ValueError, match="component"):
        integrate_vacf_to_diffusion(vacf, component="xy")
    with pytest.raises(ValueError, match="integration"):
        integrate_vacf_to_diffusion(vacf, integration="simpson")
    with pytest.raises(TypeError, match="maximum_time_ps"):
        integrate_vacf_to_diffusion(vacf, maximum_time_ps="1.0")
    with pytest.raises(ValueError, match="finite and nonnegative"):
        integrate_vacf_to_diffusion(vacf, maximum_time_ps=-0.1)


def test_result_rejects_inconsistent_running_curve() -> None:
    with pytest.raises(ValueError, match="inconsistent"):
        VACFDiffusionResult(
            lag_times=np.array([0.0, 1.0]),
            running_diffusion_a2_per_ps=np.array([0.0, 99.0]),
            integrand=np.array([1.0, 1.0]),
            dimensions=3,
            component="scalar",
            weighting="uniform",
            integration="trapezoid",
        )
