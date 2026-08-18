"""Stage 11E-GR0 analysis ownership, parity, and fail-closed tests."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis.density import (
    ArtificialBroadeningDiagnostic,
    DensityGridGeometry,
    DensityNumericalInputError,
    DensityNumericalResourceError,
    PeriodicGaussianStencilMoments,
    PeriodicMeanDiagnostic,
    PeriodicSpreadDiagnostics,
    ReciprocalResolutionDiagnostic,
    cic_assignment_covariance,
    density_grid_intervals,
    effective_artificial_broadening,
    periodic_frechet_mean_diagnostic,
    periodic_gaussian_stencil_moments,
    periodic_item_spread_diagnostics,
    prepare_density_grid_geometry,
    reciprocal_resolution_diagnostic,
    resolve_density_grid_shape,
)
from mdstats.plotting.atomic_density import (
    density_grid_intervals as plotting_density_grid_intervals,
    resolve_density_grid_shape as plotting_resolve_density_grid_shape,
)
from mdstats.plotting.density_broadening import (
    ArtificialBroadeningDiagnostic as PlottingArtificialBroadeningDiagnostic,
)
from mdstats.plotting.density_diagnostics import (
    PeriodicMeanDiagnostic as PlottingPeriodicMeanDiagnostic,
    PeriodicSpreadDiagnostics as PlottingPeriodicSpreadDiagnostics,
    ReciprocalResolutionDiagnostic as PlottingReciprocalResolutionDiagnostic,
)
from mdstats.plotting.density_kernel import (
    PeriodicGaussianStencilMoments as PlottingPeriodicGaussianStencilMoments,
    build_periodic_gaussian_stencil,
    periodic_gaussian_stencil_moments as plotting_stencil_moments,
)
from mdstats.plotting.graph_errors import GraphComplexityError

ROOT = Path(__file__).resolve().parents[1]
COMMON_MODULES = (
    ROOT / "mdstats" / "analysis" / "density" / "grid_geometry.py",
    ROOT / "mdstats" / "analysis" / "density" / "diagnostics.py",
    ROOT / "mdstats" / "analysis" / "density" / "stencil_diagnostics.py",
    ROOT / "mdstats" / "analysis" / "density" / "broadening.py",
)


def skew_cell() -> np.ndarray:
    return np.asarray(
        [[8.0, 0.0, 0.0], [3.1, 7.2, 0.0], [2.2, 1.4, 6.7]],
        dtype=np.float64,
    )


def test_common_grid_geometry_roundtrip_preserves_oblique_metric() -> None:
    cell = skew_cell()
    geometry = prepare_density_grid_geometry(cell, grid_interval=0.73)
    expected_shape = tuple(
        max(4, int(np.ceil(length / 0.73 - 1.0e-12)))
        for length in np.linalg.norm(cell, axis=1)
    )
    assert geometry.grid_shape == expected_shape
    np.testing.assert_array_equal(
        geometry.grid_step_vectors,
        cell / np.asarray(expected_shape, dtype=np.float64)[:, None],
    )
    assert geometry.realized_intervals == density_grid_intervals(cell, expected_shape)
    assert max(geometry.realized_intervals) <= 0.73
    assert geometry.logical_voxel_count == int(np.prod(expected_shape))
    restored = DensityGridGeometry.from_json_dict(geometry.to_json_dict())
    assert restored.to_json_dict() == geometry.to_json_dict()
    with pytest.raises(ValueError):
        geometry.grid_step_vectors[0, 0] = 0.0


def test_explicit_grid_and_plotting_compatibility_are_exact() -> None:
    cell = skew_cell()
    shape = (11, 9, 8)
    assert resolve_density_grid_shape(
        cell, grid_shape=shape, grid_interval=123.0
    ) == shape
    assert plotting_resolve_density_grid_shape(
        cell, grid_shape=shape, grid_interval=123.0
    ) == shape
    assert plotting_density_grid_intervals(cell, shape) == density_grid_intervals(
        cell, shape
    )
    with pytest.raises(DensityNumericalInputError, match="positive integers"):
        resolve_density_grid_shape(
            cell, grid_shape=(11, 0, 8), grid_interval=1.0
        )


def test_analysis_and_plotting_diagnostic_records_share_identity() -> None:
    assert PlottingPeriodicMeanDiagnostic is PeriodicMeanDiagnostic
    assert PlottingPeriodicSpreadDiagnostics is PeriodicSpreadDiagnostics
    assert PlottingReciprocalResolutionDiagnostic is ReciprocalResolutionDiagnostic
    assert PlottingPeriodicGaussianStencilMoments is PeriodicGaussianStencilMoments
    assert PlottingArtificialBroadeningDiagnostic is ArtificialBroadeningDiagnostic


def test_periodic_mean_and_spread_are_translation_invariant() -> None:
    cell = skew_cell()
    samples = np.asarray(
        [
            [[0.98, 0.20, 0.30], [0.25, 0.35, 0.45]],
            [[0.02, 0.22, 0.31], [0.28, 0.36, 0.46]],
            [[0.04, 0.18, 0.29], [0.24, 0.34, 0.44]],
        ]
    )
    weights = np.asarray([0.2, 0.5, 0.3])
    pbc = np.ones(3, dtype=bool)
    first = periodic_item_spread_diagnostics(
        samples, weights=weights, cell=cell, pbc=pbc, quantile=0.10
    )
    second = periodic_item_spread_diagnostics(
        samples + np.asarray([2.0, -3.0, 4.0]),
        weights=weights,
        cell=cell,
        pbc=pbc,
        quantile=0.10,
    )
    assert first.valid_reference_mask.tolist() == second.valid_reference_mask.tolist()
    assert first.required_reference_count == second.required_reference_count
    assert first.valid_reference_count == second.valid_reference_count
    assert first.reference_standard_deviation == pytest.approx(
        second.reference_standard_deviation, rel=0.0, abs=2.0e-14
    )
    np.testing.assert_allclose(
        first.standard_deviations,
        second.standard_deviations,
        rtol=0.0,
        atol=2.0e-14,
    )
    mean_a = periodic_frechet_mean_diagnostic(
        samples[:, 0, :], weights=weights, cell=cell, pbc=pbc
    )
    mean_b = periodic_frechet_mean_diagnostic(
        samples[:, 0, :] + [3.0, -2.0, 1.0],
        weights=weights,
        cell=cell,
        pbc=pbc,
    )
    np.testing.assert_allclose(mean_a.mean_cartesian, mean_b.mean_cartesian, atol=2e-13)


def test_reciprocal_resolution_matches_exhaustive_oblique_reference() -> None:
    cell = skew_cell()
    shape = (13, 10, 9)
    diagnostic = reciprocal_resolution_diagnostic(cell, shape)
    basis = 2.0 * np.pi * (np.diag(shape) @ np.linalg.inv(cell).T)
    candidates = [
        (np.linalg.norm(np.asarray(v, dtype=float) @ basis), v)
        for i in range(-7, 8)
        for j in range(-7, 8)
        for k in range(-7, 8)
        if (v := (i, j, k)) != (0, 0, 0)
    ]
    shortest = min(value for value, _vector in candidates)
    assert diagnostic.shortest_vector_norm == pytest.approx(shortest, rel=2e-14)


def test_cic_covariance_uses_cartesian_oblique_grid_steps() -> None:
    cell = skew_cell()
    shape = (10, 8, 7)
    positions = np.asarray([[0.025, 0.0625, 0.10]])
    weights = np.asarray([1.0])
    covariance, coefficients, total = cic_assignment_covariance(
        positions, weights, shape, cell
    )
    phase = (positions[0] * np.asarray(shape)) % 1.0
    expected_coefficients = phase * (1.0 - phase)
    basis = cell / np.asarray(shape, dtype=float)[:, None]
    expected_covariance = np.einsum(
        "a,ai,aj->ij", expected_coefficients, basis, basis
    )
    np.testing.assert_allclose(coefficients, expected_coefficients, atol=0.0)
    np.testing.assert_allclose(covariance, expected_covariance, rtol=2e-15, atol=2e-15)
    assert total == 1.0


def test_stencil_moments_match_dense_oracle_and_plotting_adapter() -> None:
    cell = skew_cell()
    shape = (12, 11, 10)
    sigma = 0.61
    common = periodic_gaussian_stencil_moments(
        shape,
        cell,
        sigma,
        max_candidate_contributions=10_000_000,
        max_workspace_bytes=512 * 1024**2,
    )
    plotting = plotting_stencil_moments(
        shape,
        cell,
        sigma,
        max_candidate_contributions=10_000_000,
        max_workspace_bytes=512 * 1024**2,
    )
    dense = build_periodic_gaussian_stencil(
        shape,
        cell,
        sigma,
        max_candidate_contributions=10_000_000,
        max_workspace_bytes=512 * 1024**2,
    )
    assert common.metadata_dict() == plotting.metadata_dict()
    np.testing.assert_array_equal(common.covariance, plotting.covariance)
    np.testing.assert_allclose(common.covariance, dense.covariance, rtol=0.0, atol=0.0)


def test_effective_broadening_is_covariance_sum_with_metadata_parity() -> None:
    cell = skew_cell()
    positions = np.asarray(
        [[0.10, 0.20, 0.30], [0.72, 0.81, 0.91], [0.35, 0.42, 0.53]]
    )
    weights = np.asarray([1.0, 2.0, 0.5])
    diagnostic = effective_artificial_broadening(
        positions,
        weights,
        (12, 11, 10),
        cell,
        0.55,
        max_candidate_contributions=10_000_000,
        max_workspace_bytes=512 * 1024**2,
    )
    np.testing.assert_allclose(
        diagnostic.total_covariance,
        diagnostic.cic_covariance + diagnostic.stencil_covariance,
        rtol=0.0,
        atol=0.0,
    )
    assert diagnostic.metadata_dict()["broadening_metric"] == (
        "effective_cic_stencil_rms_v1"
    )
    assert diagnostic.effective_rms == pytest.approx(
        np.sqrt(np.trace(diagnostic.total_covariance) / 3.0), rel=2e-15
    )


def test_resource_errors_remain_analysis_owned_until_plotting_boundary() -> None:
    cell = skew_cell()
    with pytest.raises(DensityNumericalResourceError, match="candidate image"):
        periodic_gaussian_stencil_moments(
            (24, 24, 24),
            cell,
            2.0,
            max_candidate_contributions=1,
            max_workspace_bytes=512 * 1024**2,
        )
    with pytest.raises(GraphComplexityError, match="candidate image"):
        plotting_stencil_moments(
            (24, 24, 24),
            cell,
            2.0,
            max_candidate_contributions=1,
            max_workspace_bytes=512 * 1024**2,
        )


def test_common_modules_do_not_import_rendering_or_graph_policy() -> None:
    forbidden = (
        "plotly",
        "graph_errors",
        "mesh",
        "browser",
        "scene_budget",
        "render_budget",
    )
    for path in COMMON_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        lowered = "\n".join(imported).lower()
        assert not any(token in lowered for token in forbidden), (path, imported)
