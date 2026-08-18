"""Focused tests for the private shared FFT correlation primitives."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.fft import rfft

from mdstats.analysis._fft import (
    linear_fft_length,
    make_atom_fft_plan,
    positive_lag_correlation_from_spectrum,
    positive_lag_pair_counts,
)


def _direct_positive_lag(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.array(
        [np.sum(x[: x.size - lag] * y[lag:]) for lag in range(x.size)],
        dtype=np.float64,
    )


@pytest.mark.parametrize("n_samples", [1, 2, 7, 8, 31, 32])
def test_linear_fft_length_is_sufficient(n_samples: int) -> None:
    n_fft = linear_fft_length(n_samples)
    assert n_fft >= 2 * n_samples - 1


def test_positive_lag_pair_counts() -> None:
    np.testing.assert_array_equal(
        positive_lag_pair_counts(6, 4),
        np.array([6.0, 5.0, 4.0, 3.0, 2.0]),
    )


def test_cross_correlation_orientation_matches_direct_sum() -> None:
    x = np.array([1.0, -2.0, 0.5, 4.0, -1.0])
    y = np.array([3.0, 0.25, -1.5, 2.0, 5.0])
    n_fft = linear_fft_length(x.size)
    spectrum = np.conj(rfft(x, n=n_fft)) * rfft(y, n=n_fft)
    actual = positive_lag_correlation_from_spectrum(
        spectrum,
        n_fft=n_fft,
        max_lag=x.size - 1,
    )
    np.testing.assert_allclose(actual, _direct_positive_lag(x, y), atol=1.0e-12)


def test_batched_spectra_preserve_leading_dimensions() -> None:
    values = np.array(
        [
            [1.0, 2.0, -1.0, 0.5],
            [-2.0, 1.5, 3.0, 4.0],
        ]
    )
    n_fft = linear_fft_length(values.shape[-1])
    transformed = rfft(values, n=n_fft, axis=-1)
    actual = positive_lag_correlation_from_spectrum(
        np.conj(transformed) * transformed,
        n_fft=n_fft,
        max_lag=values.shape[-1] - 1,
    )
    expected = np.stack([_direct_positive_lag(row, row) for row in values])
    assert actual.shape == expected.shape
    np.testing.assert_allclose(actual, expected, atol=1.0e-12)


def test_atom_fft_plan_respects_explicit_and_automatic_blocks() -> None:
    explicit = make_atom_fft_plan(10, 100, atom_block_size=3)
    assert explicit.atom_block_size == 3
    assert explicit.n_frequency == explicit.n_fft // 2 + 1

    clipped = make_atom_fft_plan(4, 100, atom_block_size=99)
    assert clipped.atom_block_size == 4

    automatic = make_atom_fft_plan(20, 100, memory_target_bytes=4096)
    assert 1 <= automatic.atom_block_size <= 20


@pytest.mark.parametrize(
    ("call", "exception"),
    [
        (lambda: linear_fft_length(0), ValueError),
        (lambda: positive_lag_pair_counts(4, 4), ValueError),
        (lambda: make_atom_fft_plan(0, 10), ValueError),
        (lambda: make_atom_fft_plan(2, 10, atom_block_size=0), ValueError),
    ],
)
def test_invalid_fft_arguments_raise(call, exception: type[Exception]) -> None:
    with pytest.raises(exception):
        call()


def test_incompatible_spectrum_shape_raises() -> None:
    with pytest.raises(ValueError, match="frequency-axis length"):
        positive_lag_correlation_from_spectrum(
            np.zeros(3, dtype=np.complex128),
            n_fft=8,
            max_lag=2,
        )
