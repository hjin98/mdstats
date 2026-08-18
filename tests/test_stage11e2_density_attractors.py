from __future__ import annotations

import copy
import inspect

import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import (
    AnalysisGeometryMetric,
    AttractorGeometry,
    CellClassification,
    ClusterComparisonStatus,
    CoreDepthSource,
    DensityAttractorCatalog,
    DensityAttractorOptions,
    DensityAttractorResourceError,
    DensityAttractorResourcePolicy,
    DensityCoordinateMeasure,
    DensityFieldErrorCertificate,
    GaussianKernelCovariance,
    PeriodicDensityDomain,
    PeriodicSpeciesDensityEstimate,
    PeriodicSpeciesDensityLadder,
    PeriodicSpeciesDensityRealization,
    SelectionValidationProtocol,
    SpeciesDensityBackend,
    SpeciesDensityIntegrals,
    TopologyStabilityStatus,
    certify_topology_refinement,
    compare_periodic_hdbscan,
    compare_periodic_kmeans,
    prepare_density_attractor_catalog,
    prepare_density_attractor_lineage,
    prepare_gaussian_image_truncation,
    prepare_scale_consensus,
)

_SHA = "1" * 64


def _periodic_delta_grid(shape: tuple[int, int, int], center: tuple[float, float, float]):
    axes = [np.arange(n, dtype=float) / n for n in shape]
    q = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    d = q - np.asarray(center)
    return d - np.rint(d)


def _derivatives(values: np.ndarray):
    shape = values.shape
    h = np.asarray([1.0 / n for n in shape])
    gradient = np.empty(shape + (3,), dtype=float)
    hessian = np.empty(shape + (3, 3), dtype=float)
    for i in range(3):
        gradient[..., i] = (np.roll(values, -1, axis=i) - np.roll(values, 1, axis=i)) / (2.0 * h[i])
        hessian[..., i, i] = (np.roll(values, -1, axis=i) - 2.0 * values + np.roll(values, 1, axis=i)) / (h[i] ** 2)
    for i in range(3):
        for j in range(i + 1, 3):
            mixed = (
                np.roll(np.roll(values, -1, axis=i), -1, axis=j)
                - np.roll(np.roll(values, -1, axis=i), 1, axis=j)
                - np.roll(np.roll(values, 1, axis=i), -1, axis=j)
                + np.roll(np.roll(values, 1, axis=i), 1, axis=j)
            ) / (4.0 * h[i] * h[j])
            hessian[..., i, j] = hessian[..., j, i] = mixed
    score = np.zeros_like(gradient)
    positive = values > 1e-300
    score[positive] = gradient[positive] / values[positive, None]
    return score, hessian


def _estimate(values: np.ndarray, *, support: np.ndarray | None = None, label: str = "h0") -> PeriodicSpeciesDensityEstimate:
    shape = values.shape
    support = np.ones(shape, dtype=bool) if support is None else np.asarray(support, dtype=bool)
    domain = PeriodicDensityDomain(
        cell=np.eye(3), registration_signature=_SHA,
        coordinate_measure=DensityCoordinateMeasure.REFERENCE_MATERIAL,
    )
    kernel = GaussianKernelCovariance(
        fractional_covariance=np.eye(3) * 0.02**2,
        label=label,
        domain_signature=domain.signature,
    )
    metric = AnalysisGeometryMetric.from_domain(domain)
    truncation = prepare_gaussian_image_truncation(kernel, relative_density_tolerance=1e-8, max_radius=2)
    values = np.asarray(values, dtype=float)
    values = np.where(support, np.maximum(values, 0.0), 0.0)
    values /= np.sum(values) / np.prod(shape)
    score, hessian = _derivatives(values)
    score[~support] = 0.0
    hessian[~support] = 0.0
    gradient = metric.raise_covectors(score.reshape(-1, 3)).reshape(score.shape)
    neff = np.where(support, 20.0, 0.0)
    realization = PeriodicSpeciesDensityRealization(
        backend=SpeciesDensityBackend.DENSE,
        grid_shape=shape,
        block_shape=shape,
        active_block_indices=np.zeros((1, 3), dtype=np.int64),
        number_density_values=values,
        probability_density_values=values,
        density_score_covector_values=score,
        metric_gradient_vector_values=gradient,
        density_hessian_covariant_values=hessian,
        local_effective_sample_size_values=neff,
        support_mask_values=support,
        number_density_standard_error_values=None,
    )
    certificate = DensityFieldErrorCertificate(
        image_density_absolute_bound=1e-12,
        image_score_covector_norm_bound=1e-10,
        image_metric_gradient_norm_bound=1e-10,
        image_hessian_frobenius_bound=1e-8,
        discrete_number_normalization_residual=0.0,
        discrete_probability_normalization_residual=0.0,
        support_node_count=int(np.count_nonzero(support)),
        total_node_count=int(np.prod(shape)),
        certified_only_on_support=True,
        truncation_signature=truncation.signature,
    )
    return PeriodicSpeciesDensityEstimate(
        species_atomic_number=11,
        species_label="Na",
        catalog_signature="2" * 64,
        domain=domain,
        kernel_covariance=kernel,
        analysis_metric=metric,
        image_truncation=truncation,
        integrals=SpeciesDensityIntegrals(
            observation_measure=1.0,
            observation_measure_units="frame",
            ion_time_integral=1.0,
            mean_occupancy_integral=1.0,
            probability_integral=1.0,
        ),
        realization=realization,
        error_certificate=certificate,
        block_uncertainty=None,
        metadata={"registration_signature": _SHA},
    )


def _point_field(shape=(20, 20, 20), center=(0.98, 0.45, 0.55), sigma=0.08):
    d = _periodic_delta_grid(shape, center)
    return np.exp(-np.sum(d * d, axis=-1) / (2 * sigma**2))


def _double_field(shape=(24, 20, 20), sigma=0.065):
    a = _point_field(shape, (0.23, 0.5, 0.5), sigma)
    b = _point_field(shape, (0.73, 0.5, 0.5), sigma)
    return a + 0.95 * b


def _annulus_field(shape=(32, 32, 20), radius=0.22, radial_sigma=0.035, z_sigma=0.06):
    d = _periodic_delta_grid(shape, (0.5, 0.5, 0.5))
    r = np.sqrt(d[..., 0] ** 2 + d[..., 1] ** 2)
    return np.exp(-((r - radius) ** 2) / (2 * radial_sigma**2) - d[..., 2] ** 2 / (2 * z_sigma**2))


def _options(**kwargs):
    values = dict(
        background_density_fraction=1e-5,
        ridge_density_fraction=0.65,
        ridge_normal_score_tolerance=6.0,
        ridge_tangential_curvature_ratio=0.65,
        minimum_ridge_nodes=8,
        plateau_relative_tolerance=1e-8,
    )
    values.update(kwargs)
    return DensityAttractorOptions(**values)


def test_boundary_crossing_point_is_one_periodic_mode_with_local_chart():
    catalog = prepare_density_attractor_catalog(_estimate(_point_field()), options=_options(ridge_density_fraction=0.9))
    points = [a for a in catalog.attractors if a.geometry is AttractorGeometry.ISOLATED_MODE]
    assert len(points) == 1
    assert min(points[0].anchor_fractional[0], 1.0 - points[0].anchor_fractional[0]) < 0.08
    assert points[0].local_chart.kind.value == "isolated_mode_chart"
    assert catalog.topology_certificate.status is TopologyStabilityStatus.UNASSESSED
    assert np.any(catalog.cell_complex.classification == CellClassification.SUPPORTED_BACKGROUND)


def test_double_well_has_supported_saddle_and_saddle_depth_cores():
    catalog = prepare_density_attractor_catalog(_estimate(_double_field()), options=_options(ridge_density_fraction=0.95))
    points = [a for a in catalog.attractors if a.geometry is AttractorGeometry.ISOLATED_MODE]
    assert len(points) == 2
    assert len(catalog.saddles) == 1
    assert catalog.saddles[0].fully_supported is True
    assert all(core.depth_source is CoreDepthSource.INTERBASIN_SADDLE_DEPTH for core in catalog.provisional_cores)
    assert all(core.resolved for core in catalog.provisional_cores)


def test_unsupported_gap_cannot_create_basin_adjacency_or_background():
    values = _double_field()
    support = np.ones_like(values, dtype=bool)
    support[10:14, :, :] = False
    support[:2, :, :] = False
    support[22:, :, :] = False
    catalog = prepare_density_attractor_catalog(_estimate(values, support=support), options=_options(ridge_density_fraction=0.95))
    assert len([a for a in catalog.attractors if a.geometry is AttractorGeometry.ISOLATED_MODE]) == 2
    assert catalog.saddles == ()
    assert np.all(catalog.cell_complex.classification[10:14] == CellClassification.UNSUPPORTED_UNKNOWN)
    assert np.all(catalog.cell_complex.classification[:2] == CellClassification.UNSUPPORTED_UNKNOWN)
    assert catalog.metadata["omitted_sparse_blocks_are_unknown"] is True


def test_annulus_is_retained_as_extended_attractor_not_arbitrary_point():
    catalog = prepare_density_attractor_catalog(
        _estimate(_annulus_field()),
        options=_options(ridge_density_fraction=0.55, ridge_normal_score_tolerance=10.0, ridge_tangential_curvature_ratio=0.85),
    )
    ridges = [a for a in catalog.attractors if a.geometry is AttractorGeometry.RIDGE_OR_MANIFOLD]
    assert len(ridges) == 1
    assert ridges[0].intrinsic_dimension == 1
    assert ridges[0].local_chart.kind.value == "annular_chart"
    assert len(ridges[0].support_node_indices) >= 8
    assert not any(a.geometry is AttractorGeometry.ISOLATED_MODE for a in catalog.attractors)


def test_bandwidth_lineage_and_unique_stable_consensus():
    estimates = tuple(_estimate(_point_field(sigma=sigma), label=f"h{i}") for i, sigma in enumerate((0.065, 0.08, 0.10)))
    ladder = PeriodicSpeciesDensityLadder(
        catalog_signature=estimates[0].catalog_signature,
        domain_signature=estimates[0].domain.signature,
        estimates=estimates,
        options_signature="3" * 64,
        resource_signature="4" * 64,
    )
    catalogs, lineage = prepare_density_attractor_lineage(ladder, options=_options(ridge_density_fraction=0.95))
    assert not lineage.ambiguous
    assert len(lineage.correspondences) == 2
    protocol = SelectionValidationProtocol(("discovery",), ("selection",), require_independent_selection=True)
    decision = prepare_scale_consensus(catalogs, lineage, protocol)
    assert decision.status.value == "resolved"
    assert decision.selected_catalog_signature == catalogs[1].signature


def test_scale_split_merge_remains_explicitly_ambiguous():
    estimates = (
        _estimate(_point_field(sigma=0.11), label="broad"),
        _estimate(_double_field(sigma=0.055), label="split"),
        _estimate(_point_field(sigma=0.12), label="broad2"),
    )
    ladder = PeriodicSpeciesDensityLadder(
        catalog_signature=estimates[0].catalog_signature,
        domain_signature=estimates[0].domain.signature,
        estimates=estimates,
        options_signature="5" * 64,
        resource_signature="6" * 64,
    )
    catalogs, lineage = prepare_density_attractor_lineage(ladder, options=_options(ridge_density_fraction=0.95))
    decision = prepare_scale_consensus(catalogs, lineage, SelectionValidationProtocol(("all",)))
    assert lineage.ambiguous
    assert decision.status.value == "scale_ambiguous"
    assert decision.selected_catalog_signature is None
    assert len(decision.competing_catalog_signatures) == 3


def test_refinement_certificate_separates_field_and_topology_stability():
    a = prepare_density_attractor_catalog(_estimate(_point_field((20, 20, 20))), options=_options(ridge_density_fraction=0.95))
    b = prepare_density_attractor_catalog(_estimate(_point_field((24, 24, 24))), options=_options(ridge_density_fraction=0.95))
    series = certify_topology_refinement((a, b), a_options_metric := _estimate(_point_field()).analysis_metric, minimum_basin_overlap=0.0)
    assert series.certificate.status is TopologyStabilityStatus.STABLE
    c = prepare_density_attractor_catalog(_estimate(_double_field()), options=_options(ridge_density_fraction=0.95))
    unstable = certify_topology_refinement((a, c), a_options_metric, minimum_basin_overlap=0.0)
    assert unstable.certificate.status is TopologyStabilityStatus.UNSTABLE
    assert "attractor_count_changes" in unstable.certificate.unresolved_reasons


def test_periodic_kmeans_does_not_split_boundary_cluster_and_hdbscan_is_diagnostic():
    metric = _estimate(_point_field()).analysis_metric
    samples = np.asarray([[0.98, 0.5, 0.5], [0.01, 0.49, 0.5], [0.03, 0.52, 0.5], [0.48, 0.5, 0.5], [0.52, 0.5, 0.5]])
    result = compare_periodic_kmeans(samples, metric, n_clusters=2)
    assert result.status is ClusterComparisonStatus.AVAILABLE
    assert result.labels[0] == result.labels[1] == result.labels[2]
    hdbscan = compare_periodic_hdbscan(samples, metric, min_cluster_size=2)
    assert hdbscan.status in {
        ClusterComparisonStatus.AVAILABLE,
        ClusterComparisonStatus.OPTIONAL_DEPENDENCY_UNAVAILABLE,
        ClusterComparisonStatus.FAILED,
    }
    weighted = compare_periodic_hdbscan(samples, metric, min_cluster_size=2, weights=np.arange(1, 6, dtype=float))
    assert weighted.status is ClusterComparisonStatus.UNSUPPORTED_WEIGHTS


def test_serialization_replay_and_tamper_rejection():
    catalog = prepare_density_attractor_catalog(_estimate(_double_field()), options=_options(ridge_density_fraction=0.95))
    payload = catalog.to_dict()
    replay = DensityAttractorCatalog.from_dict(payload)
    assert replay.signature == catalog.signature
    np.testing.assert_array_equal(replay.cell_complex.basin_owner, catalog.cell_complex.basin_owner)
    tampered = copy.deepcopy(payload)
    tampered["attractors"][0]["peak_density"] *= 1.01
    with pytest.raises(Exception):
        DensityAttractorCatalog.from_dict(tampered)


def test_resource_preflight_is_transactional():
    estimate = _estimate(_point_field())
    with pytest.raises(DensityAttractorResourceError, match="grid nodes"):
        prepare_density_attractor_catalog(
            estimate,
            options=_options(),
            resources=DensityAttractorResourcePolicy(max_grid_nodes=100),
        )


def test_selection_validation_protocol_rejects_leakage():
    with pytest.raises(Exception, match="overlap"):
        SelectionValidationProtocol(("block-a",), ("block-a",), require_independent_selection=True)
    protocol = SelectionValidationProtocol(("block-a",), ("block-b",), ("block-c",), True, True)
    assert len(protocol.signature) == 64


def test_public_api_and_scientific_ownership_exclude_rendering_backends():
    assert mdstats.DENSITY_ATTRACTOR_STAGE == "11E2"
    assert mdstats.prepare_density_attractor_catalog is prepare_density_attractor_catalog
    source = inspect.getsource(prepare_density_attractor_catalog)
    assert "plotly" not in source.lower()
    assert "marching" not in source.lower()
    assert "mesh" not in source.lower()
