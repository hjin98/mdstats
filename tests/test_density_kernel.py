"""LD0-K canonical discrete periodized Gaussian operator tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting import (
    DENSITY_STENCIL_SCHEMA,
    DensityKernelOptions,
    PeriodicGaussianStencil,
    build_periodic_gaussian_stencil,
    convolve_periodic_stencil_direct,
    convolve_periodic_stencil_fft,
    gaussian_cutoff_radius,
    smooth_periodic_node_masses,
)
from mdstats.plotting.density_contracts import DISCRETE_PERIODIZED_OPERATOR
from mdstats.plotting.graph_errors import GraphComplexityError


def lta_cell() -> np.ndarray:
    return np.asarray(
        [
            [10.0, 0.0, 0.0],
            [5.0, 8.660254037844386, 0.0],
            [5.0, 2.886751345948129, 8.16496580927726],
        ],
        dtype=np.float64,
    )


def relative_errors(reference: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    delta = np.abs(candidate - reference)
    l1 = float(np.sum(delta)) / max(1.0e-300, float(np.sum(np.abs(reference))))
    linf = float(np.max(delta)) / max(1.0e-300, float(np.max(np.abs(reference))))
    return l1, linf


def assert_direct_fft_agree(
    mass: np.ndarray,
    stencil: PeriodicGaussianStencil,
) -> None:
    direct = convolve_periodic_stencil_direct(mass, stencil)
    fft = convolve_periodic_stencil_fft(mass, stencil)
    l1, linf = relative_errors(direct, fft)
    assert l1 <= 5.0e-12
    assert linf <= 2.0e-11
    assert float(np.sum(direct)) == pytest.approx(float(np.sum(mass)), abs=5.0e-13)
    assert float(np.sum(fft)) == pytest.approx(float(np.sum(mass)), abs=5.0e-13)


def test_zero_bandwidth_stencil_is_exact_identity() -> None:
    stencil = build_periodic_gaussian_stencil((7, 8, 9), np.eye(3) * 4.0, 0.0)
    assert stencil.schema_version == DENSITY_STENCIL_SCHEMA
    assert stencil.stencil_offset_count == 1
    assert stencil.periodic_image_contribution_count == 1
    assert stencil.active_flat_indices.tolist() == [0]
    assert stencil.active_weights.tolist() == [1.0]
    assert np.count_nonzero(stencil.values) == 1
    assert stencil.values[0, 0, 0] == 1.0
    np.testing.assert_array_equal(stencil.covariance, np.zeros((3, 3)))


def test_stencil_is_nonnegative_normalized_and_deterministic() -> None:
    first = build_periodic_gaussian_stencil((12, 11, 10), lta_cell(), 0.72)
    second = build_periodic_gaussian_stencil((12, 11, 10), lta_cell(), 0.72)
    assert float(np.sum(first.values)) == pytest.approx(1.0, abs=5.0e-15)
    assert np.min(first.values) >= 0.0
    np.testing.assert_array_equal(first.values, second.values)
    np.testing.assert_array_equal(first.active_flat_indices, second.active_flat_indices)
    np.testing.assert_array_equal(first.active_weights, second.active_weights)
    np.testing.assert_array_equal(first.covariance, second.covariance)
    assert first.metadata.canonical_json() == second.metadata.canonical_json()
    assert np.array_equal(
        first.active_weights,
        first.values.reshape(-1)[first.active_flat_indices],
    )


def test_cutoff_grows_when_tail_tolerance_decreases() -> None:
    loose = gaussian_cutoff_radius(0.5, 1.0e-3)
    default = gaussian_cutoff_radius(0.5, 1.0e-8)
    strict = gaussian_cutoff_radius(0.5, 1.0e-15)
    assert 0.0 < loose < default < strict


def test_covariance_is_symmetric_positive_semidefinite() -> None:
    stencil = build_periodic_gaussian_stencil((14, 13, 12), lta_cell(), 0.61)
    np.testing.assert_allclose(stencil.covariance, stencil.covariance.T, atol=1.0e-14)
    eigenvalues = np.linalg.eigvalsh(stencil.covariance)
    assert float(np.min(eigenvalues)) >= -5.0e-13


@pytest.mark.parametrize(
    ("shape", "cell", "sigma"),
    [
        ((9, 8, 7), np.diag([5.0, 6.0, 7.0]), 0.7),
        ((10, 9, 8), lta_cell(), 0.8),
        # The cutoff exceeds the cell length, so multiple periodic images
        # contribute to at least one canonical offset.
        ((8, 8, 8), np.eye(3) * 3.0, 1.0),
    ],
)
def test_direct_and_fft_convolution_agree(
    shape: tuple[int, int, int],
    cell: np.ndarray,
    sigma: float,
) -> None:
    rng = np.random.default_rng(20260720)
    mass = rng.random(shape)
    mass /= float(np.sum(mass))
    stencil = build_periodic_gaussian_stencil(shape, cell, sigma)
    assert_direct_fft_agree(mass, stencil)


def test_cic_like_sparse_mass_direct_and_fft_agree() -> None:
    shape = (16, 15, 14)
    mass = np.zeros(shape, dtype=np.float64)
    mass[1, 2, 3] = 0.125
    mass[2, 2, 3] = 0.375
    mass[-1, 0, 0] = 0.5
    stencil = build_periodic_gaussian_stencil(shape, lta_cell(), 0.55)
    assert_direct_fft_agree(mass, stencil)


def test_multiple_periodic_images_are_aggregated() -> None:
    stencil = build_periodic_gaussian_stencil((8, 8, 8), np.eye(3) * 3.0, 1.0)
    assert stencil.periodic_image_contribution_count > stencil.stencil_offset_count
    assert stencil.cutoff_radius > 3.0
    assert float(np.sum(stencil.values)) == pytest.approx(1.0, abs=5.0e-15)


def test_smoothing_dispatch_identity_avoids_nontrivial_stencil() -> None:
    mass = np.zeros((6, 7, 8), dtype=np.float64)
    mass[2, 3, 4] = 1.0
    result, metadata = smooth_periodic_node_masses(
        mass,
        np.eye(3) * 5.0,
        0.0,
        DensityKernelOptions(smoothing_operator=DISCRETE_PERIODIZED_OPERATOR),
    )
    np.testing.assert_array_equal(result, mass)
    assert metadata["canonical_convolution_method"] == "identity"
    assert metadata["stencil_offset_count"] == 1


def test_support_safety_limit_fails_before_enumeration() -> None:
    with pytest.raises(GraphComplexityError, match="candidate image contributions"):
        build_periodic_gaussian_stencil(
            (8, 8, 8),
            np.eye(3) * 3.0,
            1.0,
            max_candidate_contributions=100,
        )
