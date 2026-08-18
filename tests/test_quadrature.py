from __future__ import annotations

import numpy as np
from numpy.exceptions import AxisError
import pytest
from scipy.integrate import cumulative_trapezoid

from mdstats.analysis._quadrature import cumulative_trapezoid_zero


def test_constant_function_uniform_grid_is_linear() -> None:
    x = np.linspace(0.0, 2.0, 9)
    values = np.full_like(x, 3.5)

    result = cumulative_trapezoid_zero(values, x)

    np.testing.assert_allclose(result, 3.5 * x, rtol=0.0, atol=2.0e-15)
    assert result.dtype == np.float64
    assert result.shape == values.shape
    assert result[0] == 0.0


def test_nonuniform_grid_matches_scipy_oracle() -> None:
    x = np.array([0.0, 0.1, 0.35, 0.9, 1.4], dtype=np.float64)
    values = np.exp(-x) * np.cos(1.7 * x)

    result = cumulative_trapezoid_zero(values, x)
    expected = cumulative_trapezoid(values, x=x, initial=0.0)

    np.testing.assert_allclose(result, expected, rtol=0.0, atol=0.0)


def test_multidimensional_axis_and_negative_axis() -> None:
    x = np.array([0.0, 0.2, 0.7, 1.0], dtype=np.float64)
    values = np.arange(24, dtype=np.float32).reshape(2, 3, 4)

    result = cumulative_trapezoid_zero(values, x, axis=-1)
    expected = cumulative_trapezoid(
        values.astype(np.float64), x=x, axis=2, initial=0.0
    )

    np.testing.assert_allclose(result, expected, rtol=0.0, atol=0.0)
    np.testing.assert_array_equal(result[..., 0], 0.0)


def test_single_sample_returns_exact_zero_without_mutation() -> None:
    values = np.array([[2.0], [-3.0]], dtype=np.float64)
    original = values.copy()

    result = cumulative_trapezoid_zero(values, [0.0], axis=1)

    np.testing.assert_array_equal(result, np.zeros_like(values))
    np.testing.assert_array_equal(values, original)


@pytest.mark.parametrize(
    ("coordinates", "message"),
    [
        ([[0.0, 1.0]], "one-dimensional"),
        ([], "at least one"),
        ([0.0, np.nan], "finite"),
        ([0.0, 0.0], "strictly increasing"),
        ([0.0, -1.0], "strictly increasing"),
    ],
)
def test_coordinate_validation(coordinates: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        cumulative_trapezoid_zero(np.ones(2), coordinates)


def test_values_and_shape_validation() -> None:
    with pytest.raises(ValueError, match="at least one dimension"):
        cumulative_trapezoid_zero(3.0, [0.0])
    with pytest.raises(ValueError, match="coordinate count"):
        cumulative_trapezoid_zero(np.ones((2, 3)), [0.0, 1.0], axis=1)
    with pytest.raises(ValueError, match="finite samples"):
        cumulative_trapezoid_zero([1.0, np.inf], [0.0, 1.0])
    with pytest.raises(TypeError, match="axis must be an integer"):
        cumulative_trapezoid_zero(np.ones(2), [0.0, 1.0], axis=True)
    with pytest.raises(AxisError):
        cumulative_trapezoid_zero(np.ones(2), [0.0, 1.0], axis=2)
