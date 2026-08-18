from __future__ import annotations

import copy
import json

import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import (
    DensityCoordinateMeasure,
    GaussianKernelCovariance,
    PeriodicDensityDomain,
    PeriodicSpeciesDensityEstimate,
    PeriodicSpeciesDensityInputError,
    PeriodicSpeciesDensityLadder,
    PeriodicSpeciesDensityRealization,
    PeriodicSpeciesDensityResourceError,
    SpeciesDensityBackend,
    SpeciesDensityOptions,
    SpeciesDensityResourcePolicy,
    evaluate_periodized_gaussian_oracle,
    prepare_gaussian_image_truncation,
    prepare_periodic_species_density,
    prepare_periodic_species_density_ladder,
)
from mdstats.analysis.site_samples import prepare_framework_aligned_ion_sample_catalog
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    EvidenceState,
    ForceSourceProvenance,
    FrameRegistrationPolicy,
    prepare_frame_registration,
    prepare_source_coordinate_contract,
)
from mdstats.provenance import FrameCollectionProvenance


def _cell() -> np.ndarray:
    return np.array([[5.0, 0.0, 0.0], [0.8, 5.4, 0.0], [0.3, 0.5, 6.1]])


def _collection() -> AtomisticFrameCollection:
    frac = np.asarray(
        [
            [[0.1, 0.1, 0.1], [0.96, 0.20, 0.30], [0.35, 0.60, 0.70]],
            [[0.1, 0.1, 0.1], [0.99, 0.22, 0.30], [0.37, 0.60, 0.69]],
            [[0.1, 0.1, 0.1], [1.02, 0.24, 0.30], [0.39, 0.61, 0.68]],
            [[0.1, 0.1, 0.1], [1.05, 0.26, 0.31], [0.41, 0.62, 0.67]],
        ],
        dtype=np.float64,
    )
    return AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(20, 24, dtype=np.int64),
        atomic_numbers=np.asarray([8, 11, 11], dtype=np.int32),
        masses=np.asarray([15.999, 22.989769, 22.989769]),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(4, dtype=np.int64),
        times=np.arange(4, dtype=np.float64),
        cells=np.repeat(_cell()[None, :, :], 4, axis=0),
        origins=np.zeros((4, 3)),
        fractional_positions=frac,
        velocities=np.zeros_like(frac),
        forces=np.ones_like(frac),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-e1",
            source_files=("synthetic",),
            velocity_source="synthetic",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="internal",
        ),
    )


def _catalog():
    collection = _collection()
    source = prepare_source_coordinate_contract(
        collection,
        force_provenance=ForceSourceProvenance(
            physical_force_complete=EvidenceState.PRESENT,
            bias_or_constraint_force=EvidenceState.ABSENT,
            stochastic_or_thermostat_force=EvidenceState.ABSENT,
        ),
    )
    registration = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(spatial_policy="physical", require_fixed_registered_cell=True),
        source_contract=source,
    )
    catalog = prepare_framework_aligned_ion_sample_catalog(
        collection, registration, species_atomic_number=11, species_label="Na"
    )
    return collection, registration, catalog


def _domain(registration, **kwargs):
    return PeriodicDensityDomain(
        cell=_cell(), registration_signature=registration.signature, **kwargs
    )


def _resources(**kwargs):
    values = dict(
        max_grid_nodes=100_000,
        max_samples=100_000,
        max_image_terms=50_000_000,
        max_workspace_bytes=64 * 1024**2,
        max_output_bytes=128 * 1024**2,
        max_blocks=100_000,
    )
    values.update(kwargs)
    return SpeciesDensityResourcePolicy(**values)


def _options(**kwargs):
    values = dict(
        grid_shape=(12, 11, 10),
        query_batch_size=128,
        sample_batch_size=8,
        relative_image_tolerance=1.0e-10,
        max_image_radius=4,
        minimum_effective_samples=1.0,
    )
    values.update(kwargs)
    return SpeciesDensityOptions(**values)


def test_periodized_oracle_is_periodic_and_has_explicit_tail_certificate():
    _, registration, _ = _catalog()
    domain = _domain(registration)
    kernel = GaussianKernelCovariance.isotropic_cartesian(0.45, domain)
    truncation = prepare_gaussian_image_truncation(
        kernel, relative_density_tolerance=1.0e-10, max_radius=4
    )
    assert truncation.relative_peak_density_bound <= 1.0e-10
    points = np.asarray([[0.02, 0.3, 0.4], [0.77, 0.2, 0.9]])
    samples = np.asarray([[0.98, 0.3, 0.4]])
    weights = np.asarray([1.0])
    rho, grad, hess = evaluate_periodized_gaussian_oracle(
        points, samples, weights, kernel, truncation=truncation
    )
    shifted, shifted_grad, shifted_hess = evaluate_periodized_gaussian_oracle(
        points + np.asarray([1.0, -2.0, 3.0]), samples, weights, kernel, truncation=truncation
    )
    np.testing.assert_allclose(rho, shifted, rtol=0.0, atol=2.0e-14)
    np.testing.assert_allclose(grad, shifted_grad, rtol=0.0, atol=3.0e-12)
    np.testing.assert_allclose(hess, shifted_hess, rtol=0.0, atol=2.0e-11)
    assert rho[0] > rho[1]


def test_number_probability_integrals_score_and_metric_gradient_are_separate():
    _, registration, catalog = _catalog()
    domain = _domain(registration)
    kernel = GaussianKernelCovariance.isotropic_cartesian(0.55, domain)
    result = prepare_periodic_species_density(
        catalog, domain, kernel, options=_options(), resources=_resources()
    )
    assert result.number_density_integral == pytest.approx(2.0, abs=2.0e-13)
    assert result.probability_density_integral == pytest.approx(1.0, abs=2.0e-13)
    assert result.integrals.ion_time_integral == pytest.approx(6.0)
    assert result.integrals.observation_measure == pytest.approx(3.0)
    assert result.integrals.mean_occupancy_integral == pytest.approx(2.0)
    support = result.realization.support_mask_dense()
    score = result.realization.density_score_covector_dense()
    gradient = result.realization.metric_gradient_vector_dense()
    expected = np.einsum(
        "ni,ij->nj", score[support], result.analysis_metric.contravariant
    )
    np.testing.assert_allclose(gradient[support], expected, rtol=2.0e-13, atol=2.0e-13)
    np.testing.assert_array_equal(score[~support], 0.0)
    assert result.metadata["minimum_image_gaussian_used"] is False
    assert result.error_certificate.certified_only_on_support is True


def test_dense_and_block_sparse_are_identical_under_same_operator():
    _, registration, catalog = _catalog()
    domain = _domain(registration)
    kernel = GaussianKernelCovariance.isotropic_cartesian(0.50, domain)
    dense = prepare_periodic_species_density(
        catalog, domain, kernel,
        options=_options(backend=SpeciesDensityBackend.DENSE), resources=_resources()
    )
    sparse = prepare_periodic_species_density(
        catalog, domain, kernel,
        options=_options(backend=SpeciesDensityBackend.BLOCK_SPARSE, block_shape=(5, 4, 3)),
        resources=_resources(),
    )
    np.testing.assert_array_equal(
        dense.realization.number_density_dense(), sparse.realization.number_density_dense()
    )
    np.testing.assert_array_equal(
        dense.realization.probability_density_dense(), sparse.realization.probability_density_dense()
    )
    np.testing.assert_array_equal(
        dense.realization.support_mask_dense(), sparse.realization.support_mask_dense()
    )
    np.testing.assert_allclose(
        dense.realization.density_score_covector_dense(),
        sparse.realization.density_score_covector_dense(),
        rtol=0.0, atol=0.0, equal_nan=True,
    )
    assert sparse.realization.active_block_count > 1
    query = np.asarray([[0, 0, 0], [12, -1, 10]])
    np.testing.assert_array_equal(
        sparse.realization.gather_number_density(query),
        dense.realization.gather_number_density(query),
    )


def test_cartesian_covariance_transforms_consistently_under_fixed_axis_permutation():
    _, registration, _ = _catalog()
    domain = _domain(registration)
    cart = np.diag([0.20**2, 0.35**2, 0.50**2])
    kernel = GaussianKernelCovariance.from_cartesian(cart, domain)
    permutation = np.asarray([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=np.float64)
    transformed_domain = PeriodicDensityDomain(
        cell=permutation @ domain.cell,
        registration_signature=registration.signature,
    )
    transformed_cart = cart
    transformed_kernel = GaussianKernelCovariance.from_cartesian(
        transformed_cart, transformed_domain
    )
    # s' = s P^T for the row-coordinate convention when H' = P H.
    samples = np.asarray([[0.13, 0.42, 0.71]])
    queries = np.asarray([[0.21, 0.38, 0.66], [0.85, 0.05, 0.20]])
    first, _, _ = evaluate_periodized_gaussian_oracle(
        queries, samples, np.ones(1), kernel, relative_image_tolerance=1e-10, max_image_radius=4
    )
    second, _, _ = evaluate_periodized_gaussian_oracle(
        queries @ permutation.T,
        samples @ permutation.T,
        np.ones(1),
        transformed_kernel,
        relative_image_tolerance=1e-10,
        max_image_radius=4,
    )
    np.testing.assert_allclose(first, second, rtol=5.0e-13, atol=5.0e-13)


def test_analysis_metric_exposes_consistent_orthonormal_chart_transforms():
    _, registration, catalog = _catalog()
    domain = _domain(registration)
    kernel = GaussianKernelCovariance.isotropic_cartesian(0.55, domain)
    result = prepare_periodic_species_density(
        catalog, domain, kernel, options=_options(), resources=_resources()
    )
    metric = result.analysis_metric
    np.testing.assert_allclose(
        metric.orthonormal_factor @ metric.orthonormal_factor.T,
        metric.covariant,
        rtol=2e-14,
        atol=2e-14,
    )
    support = result.realization.support_mask_dense()
    score = result.realization.density_score_covector_dense()[support]
    orthogonal_score = metric.covectors_in_orthonormal_chart(score)
    # Covector norm in q coordinates equals Euclidean norm in y coordinates.
    metric_norm_sq = np.einsum("ni,ij,nj->n", score, metric.contravariant, score)
    euclidean_norm_sq = np.einsum("ni,ni->n", orthogonal_score, orthogonal_score)
    np.testing.assert_allclose(metric_norm_sq, euclidean_norm_sq, rtol=5e-13, atol=5e-13)

    hessian = result.realization.density_hessian_covariant_dense()[support]
    orthogonal_hessian = metric.hessians_in_orthonormal_chart(hessian)
    displacement_y = np.asarray([0.3, -0.4, 0.2])
    displacement_q = displacement_y @ np.linalg.inv(metric.orthonormal_factor)
    q_quadratic = np.einsum("i,nij,j->n", displacement_q, hessian, displacement_q)
    y_quadratic = np.einsum("i,nij,j->n", displacement_y, orthogonal_hessian, displacement_y)
    np.testing.assert_allclose(q_quadratic, y_quadratic, rtol=5e-13, atol=5e-13)


def test_variable_cell_physical_density_is_rejected_but_reference_measure_is_explicit():
    _, registration, _ = _catalog()
    with pytest.raises(PeriodicSpeciesDensityInputError, match="varying registered cell"):
        _domain(
            registration,
            coordinate_measure=DensityCoordinateMeasure.PHYSICAL_CARTESIAN,
            source_cell_variation_max=1.0e-3,
        )
    reference = _domain(
        registration,
        coordinate_measure=DensityCoordinateMeasure.REFERENCE_MATERIAL,
        source_cell_variation_max=1.0e-3,
    )
    assert reference.coordinate_measure is DensityCoordinateMeasure.REFERENCE_MATERIAL


def test_bandwidth_ladder_and_complete_system_block_uncertainty():
    _, registration, catalog = _catalog()
    domain = _domain(registration)
    base = GaussianKernelCovariance.isotropic_cartesian(0.42, domain, label="fine")
    coarse = base.scaled(1.5, label="coarse")
    ladder = prepare_periodic_species_density_ladder(
        catalog,
        domain,
        (fine := base, coarse),
        options=_options(uncertainty_blocks=2),
        resources=_resources(),
    )
    assert ladder.bandwidth_labels == ("fine", "coarse")
    assert len({fine.signature, coarse.signature}) == 2
    for estimate in ladder.estimates:
        assert estimate.block_uncertainty is not None
        assert estimate.block_uncertainty.block_count == 2
        assert estimate.block_uncertainty.number_density_standard_error.shape == _options().grid_shape
        assert estimate.number_density_integral == pytest.approx(2.0, abs=2e-13)
    replay = PeriodicSpeciesDensityLadder.from_dict(ladder.to_dict())
    assert replay.signature == ladder.signature
    np.testing.assert_array_equal(
        replay.estimates[0].realization.number_density_dense(),
        ladder.estimates[0].realization.number_density_dense(),
    )


def test_realization_serialization_is_tamper_evident_and_resources_preflight():
    _, registration, catalog = _catalog()
    domain = _domain(registration)
    kernel = GaussianKernelCovariance.isotropic_cartesian(0.50, domain)
    result = prepare_periodic_species_density(
        catalog, domain, kernel, options=_options(), resources=_resources()
    )
    payload = result.realization.to_dict()
    replay = PeriodicSpeciesDensityRealization.from_dict(payload)
    assert replay.signature == result.realization.signature
    estimate_replay = PeriodicSpeciesDensityEstimate.from_dict(result.to_dict())
    assert estimate_replay.signature == result.signature
    json.dumps(result.to_dict(), allow_nan=False)
    tampered = copy.deepcopy(payload)
    tampered["number_density_values"][0][0][0] += 0.1
    with pytest.raises(PeriodicSpeciesDensityInputError, match="signature"):
        PeriodicSpeciesDensityRealization.from_dict(tampered)
    with pytest.raises(PeriodicSpeciesDensityResourceError, match="Grid node count"):
        prepare_periodic_species_density(
            catalog,
            domain,
            kernel,
            options=_options(grid_shape=(20, 20, 20)),
            resources=_resources(max_grid_nodes=100),
        )


def test_stage11e1_public_api_and_source_binding():
    _, registration, catalog = _catalog()
    domain = _domain(registration)
    other = PeriodicDensityDomain(
        cell=_cell(), registration_signature="0" * 64
    )
    kernel = GaussianKernelCovariance.isotropic_cartesian(0.5, domain)
    with pytest.raises(PeriodicSpeciesDensityInputError, match="registration signatures"):
        prepare_periodic_species_density(catalog, other, kernel, options=_options(), resources=_resources())
    for name in (
        "PeriodicDensityDomain",
        "GaussianKernelCovariance",
        "SpeciesDensityOptions",
        "prepare_periodic_species_density",
        "prepare_periodic_species_density_ladder",
    ):
        assert hasattr(mdstats, name)
