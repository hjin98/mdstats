"""LD0-B effective CIC-plus-stencil broadening tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    DISCRETE_PERIODIZED_OPERATOR,
    EFFECTIVE_CIC_STENCIL_BROADENING,
    AtomicDensityOptions,
    AtomicDensitySelection,
    DensityKernelOptions,
    DensityResolutionOptions,
    FrameworkDensityOptions,
)
from mdstats.plotting.atomic_density import (
    prepare_atomic_density_fields,
    resolve_density_numerics,
)
from mdstats.plotting.density_broadening import (
    cic_assignment_covariance,
    effective_artificial_broadening,
)
from mdstats.plotting.density_kernel import (
    build_periodic_gaussian_stencil,
    periodic_gaussian_stencil_moments,
)
from mdstats.plotting.framework_dynamics import prepare_framework_dynamics_scene
from tests.test_atomic_density import base_fractional, make_collection
from tests.test_framework_density import (
    bent_fractional,
    make_collection as make_framework_collection,
    topology_for,
)


def _brute_cic_covariance(
    fractional: np.ndarray,
    weights: np.ndarray,
    shape: tuple[int, int, int],
    cell: np.ndarray,
) -> np.ndarray:
    folded = fractional - np.floor(fractional)
    scaled = folded * np.asarray(shape, dtype=float)[None, :]
    phase = scaled - np.floor(scaled)
    basis = cell / np.asarray(shape, dtype=float)[:, None]
    total = float(np.sum(weights))
    covariance = np.zeros((3, 3), dtype=float)
    for sample, sample_weight in zip(phase, weights, strict=True):
        for ox in (0, 1):
            wx = 1.0 - sample[0] if ox == 0 else sample[0]
            for oy in (0, 1):
                wy = 1.0 - sample[1] if oy == 0 else sample[1]
                for oz in (0, 1):
                    wz = 1.0 - sample[2] if oz == 0 else sample[2]
                    displacement = (
                        (ox - sample[0]) * basis[0]
                        + (oy - sample[1]) * basis[1]
                        + (oz - sample[2]) * basis[2]
                    )
                    probability = wx * wy * wz
                    covariance += (
                        sample_weight
                        * probability
                        * np.outer(displacement, displacement)
                    )
    return covariance / total


def test_analytic_cic_covariance_matches_brute_force() -> None:
    cell = np.asarray(
        [[5.0, 0.0, 0.0], [1.2, 4.5, 0.0], [0.8, 0.7, 4.1]],
        dtype=float,
    )
    shape = (17, 19, 23)
    fractional = np.asarray(
        [[0.13, 0.27, 0.39], [1.71, -0.22, 0.94], [0.5, 0.5, 0.5]],
        dtype=float,
    )
    weights = np.asarray([0.2, 1.7, 0.6], dtype=float)
    analytic, coefficients, weight_sum = cic_assignment_covariance(
        fractional, weights, shape, cell
    )
    brute = _brute_cic_covariance(fractional, weights, shape, cell)
    denominator = max(1.0, float(np.linalg.norm(brute, ord="fro")))
    assert np.linalg.norm(analytic - brute, ord="fro") / denominator <= 5.0e-13
    assert np.all(coefficients >= 0.0)
    assert np.all(coefficients <= 0.25 + 1.0e-15)
    assert weight_sum == pytest.approx(float(np.sum(weights)))


def test_on_node_and_half_node_cic_covariance_limits() -> None:
    cell = np.asarray(
        [[4.0, 0.0, 0.0], [1.0, 3.5, 0.0], [0.4, 0.8, 3.0]],
        dtype=float,
    )
    shape = (8, 10, 12)
    on_node = np.asarray([[2.0 / 8.0, 4.0 / 10.0, 7.0 / 12.0]])
    covariance, coefficients, _ = cic_assignment_covariance(
        on_node, np.ones(1), shape, cell
    )
    np.testing.assert_array_equal(covariance, np.zeros((3, 3)))
    np.testing.assert_array_equal(coefficients, np.zeros(3))

    half_node = np.asarray([[2.5 / 8.0, 4.5 / 10.0, 7.5 / 12.0]])
    covariance, coefficients, _ = cic_assignment_covariance(
        half_node, np.ones(1), shape, cell
    )
    basis = cell / np.asarray(shape, dtype=float)[:, None]
    expected = 0.25 * np.einsum("ai,aj->ij", basis, basis)
    np.testing.assert_allclose(covariance, expected, rtol=0.0, atol=5.0e-15)
    np.testing.assert_allclose(coefficients, np.full(3, 0.25), rtol=0.0, atol=5.0e-15)


def test_covariance_only_stencil_matches_full_stencil() -> None:
    cell = np.asarray(
        [[6.0, 0.0, 0.0], [3.0, 5.196152423, 0.0], [3.0, 1.732050808, 4.898979486]],
        dtype=float,
    )
    shape = (31, 29, 27)
    moments = periodic_gaussian_stencil_moments(shape, cell, 0.42)
    stencil = build_periodic_gaussian_stencil(shape, cell, 0.42)
    denominator = max(1.0, float(np.linalg.norm(stencil.covariance, ord="fro")))
    assert (
        np.linalg.norm(moments.covariance - stencil.covariance, ord="fro")
        / denominator
        <= 5.0e-13
    )
    assert moments.pre_normalization_sum == pytest.approx(
        stencil.pre_normalization_sum, rel=5.0e-15
    )
    assert (
        moments.periodic_image_contribution_count
        == stencil.periodic_image_contribution_count
    )
    assert moments.metadata["dense_stencil_allocated"] is False


def test_zero_bandwidth_effective_width_is_cic_only() -> None:
    diagnostic = effective_artificial_broadening(
        np.asarray([[0.125, 0.25, 0.375], [0.4, 0.3, 0.2]]),
        np.asarray([0.25, 0.75]),
        (8, 8, 8),
        np.eye(3) * 4.0,
        0.0,
    )
    np.testing.assert_array_equal(
        diagnostic.stencil_covariance, np.zeros((3, 3))
    )
    assert diagnostic.stencil_rms == 0.0
    assert diagnostic.effective_rms == pytest.approx(diagnostic.cic_rms)


def test_effective_adaptive_resolution_reaches_target() -> None:
    frac = base_fractional(2)
    frac[:, 3, :] = np.asarray(
        [[0.45, 0.50, 0.50], [0.55, 0.50, 0.50]], dtype=float
    )
    cell = np.eye(3) * 2.0
    options = AtomicDensityOptions(
        resolution_options=DensityResolutionOptions(
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
            max_smearing_to_sample_sd_ratio=1.0,
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    with pytest.warns(RuntimeWarning, match="effective artificial RMS"):
        numerics = resolve_density_numerics(
            cell,
            options=options,
            fractional_by_frame=frac[:, 3:4, :],
            frame_weights=np.asarray([0.5, 0.5]),
            pbc=np.ones(3, dtype=bool),
            max_voxels=1_000_000,
            field_label="effective test",
        )
    assert numerics.adaptive_triggered is True
    assert numerics.adaptive_budget_limited is False
    assert numerics.adaptive_target_achieved is True
    assert numerics.broadening_diagnostic is not None
    assert numerics.adaptive_target_width is not None
    assert (
        numerics.broadening_diagnostic.effective_rms
        <= numerics.adaptive_target_width + 5.0e-13
    )


def test_effective_explicit_grid_reports_unresolved_target() -> None:
    frac = base_fractional(2)
    frac[:, 3, :] = np.asarray(
        [[0.49, 0.50, 0.50], [0.51, 0.50, 0.50]], dtype=float
    )
    options = AtomicDensityOptions(
        resolution_options=DensityResolutionOptions(
            grid_shape=(16, 16, 16),
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    with pytest.warns(RuntimeWarning, match="explicitly fixed"):
        numerics = resolve_density_numerics(
            np.eye(3) * 10.0,
            options=options,
            fractional_by_frame=frac[:, 3:4, :],
            frame_weights=np.asarray([0.5, 0.5]),
            pbc=np.ones(3, dtype=bool),
            max_voxels=1_000_000,
            field_label="explicit test",
        )
    assert numerics.grid_shape == (16, 16, 16)
    assert numerics.adaptive_triggered is False
    assert numerics.adaptive_target_achieved is False


def test_atomic_field_records_effective_broadening_metadata() -> None:
    frac = base_fractional(2)
    frac[:, 3, :] = np.asarray(
        [[0.40, 0.50, 0.50], [0.60, 0.50, 0.50]], dtype=float
    )
    collection = make_collection(frac)
    options = AtomicDensityOptions(
        resolution_options=DensityResolutionOptions(
            grid_shape=(16, 16, 16),
            gaussian_bandwidth=0.4,
            adaptive_smearing=False,
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    field = prepare_atomic_density_fields(
        collection,
        frame_indices=(0, 1),
        frame_weights=np.asarray([0.5, 0.5]),
        display_cell=np.eye(3) * 10.0,
        registration_mode="material",
        framework_drift=np.zeros((2, 3)),
        selections=(AtomicDensitySelection(atom_indices=(3,)),),
        options=options,
        max_fields=1,
        max_total_voxels=100_000,
        max_samples=100,
    )[0]
    assert field.metadata["broadening_metric"] == EFFECTIVE_CIC_STENCIL_BROADENING
    assert field.metadata["effective_artificial_rms"] > 0.0
    assert field.metadata["cic_assignment_rms"] >= 0.0
    assert field.metadata["canonical_stencil_rms"] > 0.0
    assert field.metadata["resolution_reference_source"] == "atomic_samples"


def test_framework_edge_reports_own_effective_covariance() -> None:
    collection = make_framework_collection(bent_fractional(2))
    options = FrameworkDensityOptions(
        resolution_options=DensityResolutionOptions(
            grid_shape=(16, 16, 16),
            gaussian_bandwidth=0.5,
            adaptive_smearing=False,
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    scene = prepare_framework_dynamics_scene(
        collection,
        topology_for(collection),
        framework_density_options=options,
    )
    fields = scene.framework_density_fields
    assert fields is not None
    assert fields.vertex_density is not None
    assert fields.edge_length_density is not None
    vertex = fields.vertex_density.metadata
    edge = fields.edge_length_density.metadata
    assert vertex["resolution_reference_source"] == "framework_vertices"
    assert edge["resolution_reference_source"] == "framework_vertices"
    assert edge["broadening_sample_count"] == edge["quadrature_sample_count"]
    assert edge["resolution_reference_effective_artificial_rms"] == pytest.approx(
        vertex["effective_artificial_rms"]
    )


def test_effective_adaptive_resolution_reports_budget_limit() -> None:
    frac = base_fractional(2)
    frac[:, 3, :] = np.asarray(
        [[0.49, 0.50, 0.50], [0.51, 0.50, 0.50]], dtype=float
    )
    options = AtomicDensityOptions(
        resolution_options=DensityResolutionOptions(
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    with pytest.warns(RuntimeWarning, match="could not be reached"):
        numerics = resolve_density_numerics(
            np.eye(3) * 10.0,
            options=options,
            fractional_by_frame=frac[:, 3:4, :],
            frame_weights=np.asarray([0.5, 0.5]),
            pbc=np.ones(3, dtype=bool),
            max_voxels=125_000,
            field_label="budget test",
        )
    assert numerics.grid_shape == (50, 50, 50)
    assert numerics.adaptive_triggered is True
    assert numerics.adaptive_budget_limited is True
    assert numerics.adaptive_target_achieved is False


def test_effective_zero_spread_has_no_target_and_does_not_refine() -> None:
    fractional = np.asarray(
        [[[0.25, 0.25, 0.25]], [[0.25, 0.25, 0.25]]], dtype=float
    )
    options = AtomicDensityOptions(
        resolution_options=DensityResolutionOptions(
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
    )
    with pytest.warns(RuntimeWarning, match="no finite positive target"):
        numerics = resolve_density_numerics(
            np.eye(3) * 4.0,
            options=options,
            fractional_by_frame=fractional,
            frame_weights=np.asarray([0.5, 0.5]),
            pbc=np.ones(3, dtype=bool),
            max_voxels=1_000_000,
            field_label="zero-spread test",
        )
    assert numerics.adaptive_target_defined is False
    assert numerics.adaptive_target_width is None
    assert numerics.adaptive_target_achieved is None
    assert numerics.adaptive_triggered is False
    assert numerics.grid_shape == (20, 20, 20)
