from __future__ import annotations

import numpy as np
import pytest

from mdstats.analysis._spectral import (
    one_sided_density_scale,
    reconstruct_two_sided_correlation,
    resolve_lag_window,
    resolve_spectrum_fft_length,
    transform_positive_lag_correlation,
)
from mdstats.analysis._spectral_units import convert_frequency_axes


def test_resolve_spectrum_fft_length_honors_bounds() -> None:
    assert resolve_spectrum_fft_length(1, zero_pad_to=None) == 1
    assert resolve_spectrum_fft_length(8, zero_pad_to=None) >= 15
    assert resolve_spectrum_fft_length(8, zero_pad_to=64) >= 64
    assert resolve_spectrum_fft_length(8, zero_pad_to=2) == (
        resolve_spectrum_fft_length(8, zero_pad_to=None)
    )

    with pytest.raises(ValueError, match="positive integer"):
        resolve_spectrum_fft_length(0, zero_pad_to=None)
    with pytest.raises(TypeError, match="integer"):
        resolve_spectrum_fft_length(True, zero_pad_to=None)
    with pytest.raises(ValueError, match="positive integer"):
        resolve_spectrum_fft_length(4, zero_pad_to=0)


def test_resolve_lag_window_builtins_and_custom() -> None:
    rectangular, metadata = resolve_lag_window(None, 5)
    np.testing.assert_allclose(rectangular, 1.0)
    assert metadata["kind"] == "rectangular"

    half_hann, metadata = resolve_lag_window("half_hann", 5)
    assert metadata["name"] == "half_hann"
    assert half_hann[0] == pytest.approx(1.0)
    assert half_hann[-1] == pytest.approx(0.0)
    assert np.all(np.diff(half_hann) <= 0.0)

    tukey_zero, _ = resolve_lag_window(("half_tukey", 0.0), 5)
    np.testing.assert_allclose(tukey_zero, 1.0)
    tukey_one, _ = resolve_lag_window(("half_tukey", 1.0), 5)
    np.testing.assert_allclose(tukey_one, half_hann)

    custom = np.array([1.0, 0.8, 0.3])
    resolved, metadata = resolve_lag_window(custom, 3)
    np.testing.assert_allclose(resolved, custom)
    assert metadata["name"] == "custom"
    assert not np.shares_memory(resolved, custom)

    with pytest.raises(ValueError, match=r"window\[0\]"):
        resolve_lag_window([0.9, 0.5], 2)
    with pytest.raises(ValueError, match="shape"):
        resolve_lag_window([1.0], 2)
    with pytest.raises(ValueError, match="closed interval"):
        resolve_lag_window(("half_tukey", 1.2), 5)


def test_reconstruct_two_sided_scalar_and_tensor() -> None:
    scalar = np.array([10.0, 2.0, 3.0])
    reconstructed = reconstruct_two_sided_correlation(scalar, n_fft=7)
    np.testing.assert_allclose(reconstructed, [10.0, 2.0, 3.0, 0.0, 0.0, 3.0, 2.0])

    tensor = np.zeros((3, 2, 2), dtype=np.float64)
    tensor[0] = [[1.0, 4.0], [4.0, 2.0]]
    tensor[1] = [[3.0, 5.0], [7.0, 6.0]]
    tensor[2] = [[8.0, 9.0], [11.0, 10.0]]
    work = reconstruct_two_sided_correlation(
        tensor, n_fft=7, tensor_axes=(1, 2)
    )
    np.testing.assert_allclose(work[1], tensor[1])
    np.testing.assert_allclose(work[2], tensor[2])
    np.testing.assert_allclose(work[-1], tensor[1].T)
    np.testing.assert_allclose(work[-2], tensor[2].T)

    with pytest.raises(ValueError, match="too small"):
        reconstruct_two_sided_correlation(scalar, n_fft=4)
    with pytest.raises(ValueError, match="lag axis"):
        reconstruct_two_sided_correlation(tensor, n_fft=7, tensor_axes=(0, 2))


def test_one_sided_density_scale_even_and_odd() -> None:
    np.testing.assert_array_equal(one_sided_density_scale(1), [1.0])
    np.testing.assert_array_equal(one_sided_density_scale(5), [1.0, 2.0, 2.0])
    np.testing.assert_array_equal(one_sided_density_scale(6), [1.0, 2.0, 2.0, 1.0])


def test_transform_matches_direct_dft_and_preserves_bin_area() -> None:
    correlation = np.array([2.0, 0.25, -0.4, 0.1], dtype=np.float64)
    dt_ps = 0.2
    n_fft = resolve_spectrum_fft_length(correlation.size, zero_pad_to=11)
    frequencies, actual = transform_positive_lag_correlation(
        correlation, dt_ps=dt_ps, n_fft=n_fft
    )

    work = reconstruct_two_sided_correlation(correlation, n_fft=n_fft)
    frequency_indices = np.arange(n_fft // 2 + 1)
    sample_indices = np.arange(n_fft)
    phase = np.exp(
        -2.0j
        * np.pi
        * frequency_indices[:, None]
        * sample_indices[None, :]
        / n_fft
    )
    expected = dt_ps * (phase @ work) * one_sided_density_scale(n_fft)
    np.testing.assert_allclose(actual, expected, rtol=2e-14, atol=2e-14)

    df = frequencies[1] - frequencies[0]
    assert df * np.sum(actual.real) == pytest.approx(correlation[0], abs=2e-14)
    np.testing.assert_allclose(actual.imag, 0.0, atol=2e-14)


def test_tensor_transform_is_hermitian() -> None:
    tensor = np.zeros((4, 3, 3), dtype=np.float64)
    tensor[:, 0, 0] = [2.0, 1.0, 0.2, -0.1]
    tensor[:, 1, 1] = [1.0, 0.4, 0.1, 0.0]
    tensor[:, 2, 2] = [0.5, 0.2, 0.0, -0.05]
    tensor[0, 0, 1] = tensor[0, 1, 0] = 0.3
    tensor[1:, 0, 1] = [0.8, -0.2, 0.1]
    tensor[1:, 1, 0] = [-0.4, 0.5, 0.2]

    _, spectrum = transform_positive_lag_correlation(
        tensor,
        dt_ps=0.1,
        n_fft=resolve_spectrum_fft_length(4, zero_pad_to=None),
        tensor_axes=(1, 2),
    )
    np.testing.assert_allclose(
        spectrum,
        np.conjugate(np.swapaxes(spectrum, 1, 2)),
        atol=2e-14,
    )


def test_frequency_axis_conversions() -> None:
    frequencies = np.array([0.0, 1.0, 3.5])
    angular, wavenumbers, energies = convert_frequency_axes(frequencies)
    np.testing.assert_allclose(angular, 2.0 * np.pi * frequencies)
    assert wavenumbers[1] == pytest.approx(33.3564095198, rel=1e-10)
    assert energies[1] == pytest.approx(4.135667696, rel=1e-9)

    with pytest.raises(ValueError, match="one-dimensional"):
        convert_frequency_axes([[1.0]])
    with pytest.raises(ValueError, match="nonnegative"):
        convert_frequency_axes([-1.0])


def test_spectral_bin_integral_uses_uniform_bin_measure() -> None:
    from mdstats.analysis._spectral import spectral_bin_integral

    frequencies = np.array([0.0, 0.5, 1.0, 1.5], dtype=np.float64)
    spectrum = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
            [10.0, 11.0, 12.0],
        ],
        dtype=np.float64,
    )

    actual = spectral_bin_integral(spectrum, frequencies, axis=0)
    np.testing.assert_allclose(actual, 0.5 * np.sum(spectrum, axis=0))

    transposed = spectral_bin_integral(spectrum.T, frequencies, axis=-1)
    np.testing.assert_allclose(transposed, actual)

    cropped = spectral_bin_integral(spectrum[1:], frequencies[1:], axis=0)
    np.testing.assert_allclose(cropped, 0.5 * np.sum(spectrum[1:], axis=0))


def test_spectral_bin_integral_differs_from_trapezoidal_endpoint_weights() -> None:
    from mdstats.analysis._spectral import spectral_bin_integral

    frequencies = np.array([0.0, 1.0, 2.0], dtype=np.float64)
    spectrum = np.array([1.0, 2.0, 1.0], dtype=np.float64)

    assert spectral_bin_integral(spectrum, frequencies) == pytest.approx(4.0)
    assert np.trapezoid(spectrum, x=frequencies) == pytest.approx(3.0)


def test_spectral_bin_integral_validation() -> None:
    from numpy.exceptions import AxisError
    from mdstats.analysis._spectral import spectral_bin_integral

    with pytest.raises(TypeError, match="real"):
        spectral_bin_integral(np.array([1.0 + 1.0j, 2.0]), [0.0, 1.0])
    with pytest.raises(ValueError, match="at least one dimension"):
        spectral_bin_integral(1.0, [0.0, 1.0])
    with pytest.raises(TypeError, match="axis"):
        spectral_bin_integral([1.0, 2.0], [0.0, 1.0], axis=True)
    with pytest.raises(AxisError):
        spectral_bin_integral([1.0, 2.0], [0.0, 1.0], axis=2)
    with pytest.raises(ValueError, match="one-dimensional"):
        spectral_bin_integral([1.0, 2.0], [[0.0, 1.0]])
    with pytest.raises(ValueError, match="at least two"):
        spectral_bin_integral([1.0], [0.0])
    with pytest.raises(ValueError, match="does not match"):
        spectral_bin_integral([1.0, 2.0], [0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="finite"):
        spectral_bin_integral([1.0, np.nan], [0.0, 1.0])
    with pytest.raises(ValueError, match="nonnegative"):
        spectral_bin_integral([1.0, 2.0], [-1.0, 0.0])
    with pytest.raises(ValueError, match="strictly increasing"):
        spectral_bin_integral([1.0, 2.0], [0.0, 0.0])
    with pytest.raises(ValueError, match="uniformly spaced"):
        spectral_bin_integral([1.0, 2.0, 3.0], [0.0, 1.0, 2.2])


def test_make_atom_spectrum_plan_explicit_and_automatic_blocks() -> None:
    from mdstats.analysis._spectral import make_atom_spectrum_plan

    segment_length = 64
    n_fft = 128
    n_frequency = n_fft // 2 + 1
    bytes_per_atom = (
        3 * segment_length * np.dtype(np.float64).itemsize
        + 3 * n_fft * np.dtype(np.float64).itemsize
        + 3 * n_frequency * np.dtype(np.complex128).itemsize
        + 3 * n_frequency * np.dtype(np.float64).itemsize
    )

    explicit = make_atom_spectrum_plan(
        10,
        segment_length,
        n_fft,
        atom_block_size=4,
        memory_target_bytes=1,
    )
    assert explicit.n_fft == n_fft
    assert explicit.n_frequency == n_frequency
    assert explicit.atom_block_size == 4
    assert explicit.estimated_work_bytes == 4 * bytes_per_atom

    automatic = make_atom_spectrum_plan(
        10,
        segment_length,
        n_fft,
        atom_block_size=None,
        memory_target_bytes=3 * bytes_per_atom,
    )
    assert automatic.atom_block_size == 3
    assert automatic.estimated_work_bytes == 3 * bytes_per_atom

    clamped = make_atom_spectrum_plan(
        3,
        segment_length,
        n_fft,
        atom_block_size=99,
        memory_target_bytes=1,
    )
    assert clamped.atom_block_size == 3


def test_make_atom_spectrum_plan_small_target_keeps_one_atom() -> None:
    from mdstats.analysis._spectral import make_atom_spectrum_plan

    plan = make_atom_spectrum_plan(
        7,
        32,
        32,
        atom_block_size=None,
        memory_target_bytes=1,
    )
    assert plan.atom_block_size == 1
    assert plan.estimated_work_bytes > 1


def test_make_atom_spectrum_plan_validation() -> None:
    from mdstats.analysis._spectral import make_atom_spectrum_plan

    with pytest.raises(TypeError, match="integer"):
        make_atom_spectrum_plan(
            True, 8, 8, atom_block_size=None, memory_target_bytes=1024
        )
    with pytest.raises(ValueError, match="positive integer"):
        make_atom_spectrum_plan(
            1, 0, 8, atom_block_size=None, memory_target_bytes=1024
        )
    with pytest.raises(ValueError, match="greater than or equal"):
        make_atom_spectrum_plan(
            1, 9, 8, atom_block_size=None, memory_target_bytes=1024
        )
    with pytest.raises(ValueError, match="positive integer"):
        make_atom_spectrum_plan(
            1, 8, 8, atom_block_size=None, memory_target_bytes=0
        )
    with pytest.raises(ValueError, match="positive integer"):
        make_atom_spectrum_plan(
            1, 8, 8, atom_block_size=0, memory_target_bytes=1024
        )
