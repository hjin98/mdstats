from __future__ import annotations

import copy
import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import (
    AnalysisGeometryMetric,
    AttractorGeometry,
    AttractorLocalChart,
    CellClassification,
    CoreDepthSource,
    DecorrelationStatus,
    DensityAttractor,
    DensityAttractorCatalog,
    DensityAttractorOptions,
    DensityCoordinateMeasure,
    DensityFieldErrorCertificate,
    GaussianKernelCovariance,
    LocalChartKind,
    PassageOutcome,
    PeriodicDensityDomain,
    PeriodicSpeciesDensityEstimate,
    PeriodicSpeciesDensityRealization,
    ProvisionalCore,
    RawMembershipClass,
    SpeciesDensityBackend,
    SpeciesDensityIntegrals,
    SupportedPeriodicCellComplex,
    TemporalAssignmentInputError,
    TemporalAssignmentOptions,
    TemporalAssignmentResourceError,
    TemporalAssignmentResourcePolicy,
    TemporalEvidencePattern,
    TemporalSupportStatus,
    TopologyStabilityCertificate,
    prepare_gaussian_image_truncation,
    prepare_provisional_temporal_assignment,
)
from mdstats.analysis.site_samples import (
    prepare_framework_aligned_ion_sample_catalog,
    prepare_trajectory_segment_weighting,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    EvidenceState,
    ForceSourceProvenance,
    FrameRegistrationPolicy,
    prepare_frame_registration,
    prepare_source_coordinate_contract,
)
from mdstats.provenance import FrameCollectionProvenance


from mdstats.analysis.density.temporal_assignment import _geyer_initial_positive_sequence


def _sample_catalog(xs, *, semantics="trajectory", dt=0.1, times=None, segment_starts=()):
    xs = np.asarray(xs, dtype=float)
    n = len(xs)
    frac = np.zeros((n, 2, 3), dtype=float)
    frac[:, 0] = [0.05, 0.05, 0.05]
    frac[:, 1, 0] = np.mod(xs, 1.0)
    frac[:, 1, 1:] = 0.5
    collection = AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.arange(n, dtype=np.int64),
        atomic_numbers=np.array([8, 11], dtype=np.int32),
        masses=np.array([15.999, 22.989769]),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n, dtype=np.int64),
        times=(
            None
            if semantics == "ensemble"
            else np.asarray(times, dtype=float)
            if times is not None
            else np.arange(n, dtype=float) * dt
        ),
        cells=np.repeat(np.eye(3)[None], n, axis=0),
        origins=np.zeros((n, 3)),
        fractional_positions=frac,
        velocities=np.zeros_like(frac) if semantics == "trajectory" else None,
        forces=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic-e4",
            source_files=("synthetic",),
            velocity_source="synthetic" if semantics == "trajectory" else "unavailable",
            coordinate_normalization="native",
            stress_source=None,
            units_source="internal",
        ),
    )
    source = prepare_source_coordinate_contract(
        collection,
        force_provenance=ForceSourceProvenance(
            physical_force_complete=EvidenceState.ABSENT,
            bias_or_constraint_force=EvidenceState.ABSENT,
            stochastic_or_thermostat_force=EvidenceState.ABSENT,
        ),
    )
    registration = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(spatial_policy="physical", require_fixed_registered_cell=True),
        source_contract=source,
    )
    temporal_weighting = None
    if segment_starts:
        temporal_weighting = prepare_trajectory_segment_weighting(
            collection,
            registration=registration,
            segment_start_frame_indices=segment_starts,
            included_segment_ids=tuple(range(len(segment_starts) + 1)),
        )
    return prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        species_label="Na",
        temporal_weighting=temporal_weighting,
    )


def _density_and_attractors(catalog, *, unknown_x=None):
    shape = (20, 1, 1)
    domain = PeriodicDensityDomain(
        cell=np.eye(3),
        registration_signature=catalog.registration_signature,
        coordinate_measure=DensityCoordinateMeasure.REFERENCE_MATERIAL,
    )
    kernel = GaussianKernelCovariance.isotropic_cartesian(0.06, domain)
    metric = AnalysisGeometryMetric.from_domain(domain)
    truncation = prepare_gaussian_image_truncation(kernel, relative_density_tolerance=1e-8, max_radius=2)
    values = np.ones(shape, dtype=float)
    score = np.zeros(shape + (3,), dtype=float)
    hessian = np.zeros(shape + (3, 3), dtype=float)
    support = np.ones(shape, dtype=bool)
    realization = PeriodicSpeciesDensityRealization(
        backend=SpeciesDensityBackend.DENSE,
        grid_shape=shape,
        block_shape=shape,
        active_block_indices=np.zeros((1, 3), dtype=np.int64),
        number_density_values=values,
        probability_density_values=values,
        density_score_covector_values=score,
        metric_gradient_vector_values=score,
        density_hessian_covariant_values=hessian,
        local_effective_sample_size_values=np.full(shape, 20.0),
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
        support_node_count=20,
        total_node_count=20,
        certified_only_on_support=True,
        truncation_signature=truncation.signature,
    )
    estimate = PeriodicSpeciesDensityEstimate(
        species_atomic_number=11,
        species_label="Na",
        catalog_signature=catalog.signature,
        domain=domain,
        kernel_covariance=kernel,
        analysis_metric=metric,
        image_truncation=truncation,
        integrals=SpeciesDensityIntegrals(
            observation_measure=1.0,
            observation_measure_units="ps",
            ion_time_integral=1.0,
            mean_occupancy_integral=1.0,
            probability_integral=1.0,
        ),
        realization=realization,
        error_certificate=certificate,
        block_uncertainty=None,
        metadata={"registration_signature": catalog.registration_signature},
    )
    classification = np.full(shape, CellClassification.SUPPORTED_TRANSITION_REGION, dtype=np.uint8)
    owner = np.full(shape, -1, dtype=np.int32)
    classification[0] = CellClassification.SUPPORTED_BACKGROUND
    classification[1:8] = CellClassification.SUPPORTED_BASIN
    owner[1:8] = 0
    classification[11:18] = CellClassification.SUPPORTED_BASIN
    owner[11:18] = 1
    support_mask = np.ones(shape, dtype=bool)
    if unknown_x is not None:
        classification[unknown_x] = CellClassification.UNSUPPORTED_UNKNOWN
        support_mask[unknown_x] = False
        owner[unknown_x] = -1
    successor = np.arange(20, dtype=np.int64).reshape(shape)
    complex_ = SupportedPeriodicCellComplex(shape, classification, owner, successor, support_mask)
    attractor_items = []
    cores = []
    for aid, node, anchor in ((0, 4, np.array([0.2, 0.0, 0.0])), (1, 14, np.array([0.7, 0.0, 0.0]))):
        chart = AttractorLocalChart(LocalChartKind.ISOLATED_MODE, anchor, np.array([node]), 0.2)
        attractor_items.append(DensityAttractor(
            aid,
            AttractorGeometry.ISOLATED_MODE,
            anchor,
            node,
            np.array([node]),
            1.0,
            0.5,
            0,
            np.array([-1.0, -1.0, -1.0]),
            True,
            chart,
        ))
        core_nodes = np.array([node - 1, node], dtype=np.int64)
        cores.append(ProvisionalCore(
            aid,
            CoreDepthSource.PROBABILITY_CONTENT_CORE,
            core_nodes,
            0.8,
            retained_probability=0.2,
            resolved=True,
        ))
    options = DensityAttractorOptions()
    temp = DensityAttractorCatalog(
        estimate.signature,
        domain.signature,
        kernel.signature,
        options,
        complex_,
        tuple(attractor_items),
        (),
        tuple(cores),
        None,
        (),
        {"synthetic": True},
    )
    certificate_topology = TopologyStabilityCertificate.unassessed(temp.signature)
    attractors = DensityAttractorCatalog(
        estimate.signature,
        domain.signature,
        kernel.signature,
        options,
        complex_,
        tuple(attractor_items),
        (),
        tuple(cores),
        certificate_topology,
        (),
        {"synthetic": True},
    )
    return estimate, attractors


def _run(xs, *, semantics="trajectory", unknown_x=None, **option_kwargs):
    catalog = _sample_catalog(xs, semantics=semantics)
    estimate, attractors = _density_and_attractors(catalog, unknown_x=unknown_x)
    options = TemporalAssignmentOptions(
        minimum_decorrelation_samples=6,
        maximum_autocorrelation_lag=16,
        stride_factors=(1, 2, 4),
        **option_kwargs,
    )
    resources = TemporalAssignmentResourcePolicy(
        max_samples=10_000,
        max_atoms=10,
        max_intervals=10_000,
        max_passages=10_000,
        max_autocorrelation_terms=1_000_000,
        max_output_bytes=10_000_000,
    )
    return catalog, estimate, attractors, prepare_provisional_temporal_assignment(
        catalog, estimate, attractors, options=options, resources=resources
    )


def _jitter(center, n):
    return center + 0.006 * np.sin(np.arange(n) * 1.7)



def test_geyer_initial_positive_sequence_uses_conventional_even_odd_pairs():
    inefficiency, last_lag = _geyer_initial_positive_sequence([1.0, 0.5, 0.2, 0.1, -0.4, -0.2])
    assert inefficiency == pytest.approx(1.0 + 2.0 * (0.5 + 0.2 + 0.1))
    assert last_lag == 3

    # The negative (rho[2] + rho[3]) pair truncates before either lag enters.
    inefficiency, last_lag = _geyer_initial_positive_sequence([1.0, 0.25, -0.4, 0.1, 0.9])
    assert inefficiency == pytest.approx(1.5)
    assert last_lag == 1

def test_raw_membership_keeps_transition_background_and_unknown_unfilled():
    xs = [0.2, 0.3, 0.45, 0.0, 0.50, 0.7]
    _, _, _, result = _run(xs, unknown_x=10)
    classes = [RawMembershipClass(int(v)) for v in result.membership.raw_classification]
    assert classes[0] is RawMembershipClass.CORE
    assert classes[1] is RawMembershipClass.BASIN
    assert classes[2] is RawMembershipClass.TRANSITION_REGION
    assert classes[3] is RawMembershipClass.SUPPORTED_BACKGROUND
    assert classes[4] is RawMembershipClass.UNSUPPORTED_UNKNOWN
    assert result.membership.basin_membership[2] == -1
    assert result.membership.basin_membership[3] == -1
    assert result.membership.basin_membership[4] == -1
    assert result.metadata["nearest_center_fill_performed"] is False


def test_one_jump_has_two_residences_and_distinct_pattern():
    xs = np.r_[_jitter(0.2, 14), [0.30, 0.35, 0.45, 0.50, 0.58, 0.62], _jitter(0.7, 14)]
    _, _, _, result = _run(xs)
    assert result.evidence_pattern is TemporalEvidencePattern.ONE_JUMP
    assert [p.outcome for p in result.passages] == [PassageOutcome.JUMP]
    assert result.passages[0].target_attractor_id == 1
    assert len(result.residences) == 2
    assert result.residences[0].right_censored is False
    assert result.residences[1].right_censored is True
    assert all(item.status in {DecorrelationStatus.RESOLVED, DecorrelationStatus.FRAME_ONLY_IRREGULAR_STRIDE} for item in result.decorrelation_estimates)


def test_repeated_hopping_and_fast_return_are_reported_as_recrossing():
    xs = np.r_[_jitter(0.2, 10), [0.35, 0.45, 0.60], _jitter(0.7, 3), [0.60, 0.45, 0.35], _jitter(0.2, 10)]
    _, _, _, result = _run(xs, minimum_recrossing_frames=20)
    assert result.evidence_pattern is TemporalEvidencePattern.REPEATED_HOPPING
    jumps = [p for p in result.passages if p.outcome is PassageOutcome.JUMP]
    assert len(jumps) == 2
    assert all(p.recrossing for p in jumps)


def test_short_excursion_is_not_promoted_to_jump():
    xs = np.r_[_jitter(0.2, 12), [0.35, 0.45], _jitter(0.2, 12)]
    _, _, _, result = _run(xs, minimum_short_excursion_frames=3)
    assert result.evidence_pattern is TemporalEvidencePattern.SHORT_EXCURSION_ONLY
    assert len(result.passages) == 1
    assert result.passages[0].outcome is PassageOutcome.RETURN_EXCURSION
    assert result.passages[0].short_excursion is True
    assert result.passages[0].target_attractor_id == 0


def test_unsupported_gap_blocks_resolved_jump():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.50, 0.60], _jitter(0.7, 8)]
    _, _, _, result = _run(xs, unknown_x=10)
    assert len(result.passages) == 1
    assert result.passages[0].outcome is PassageOutcome.UNRESOLVED_GAP
    assert result.passages[0].contains_unsupported_or_unresolved
    assert result.evidence_pattern is TemporalEvidencePattern.UNRESOLVED_GAPS_ONLY


def test_stride_sensitivity_is_separate_from_raw_labels():
    xs = np.r_[_jitter(0.2, 10), [0.45], _jitter(0.2, 10)]
    _, _, _, result = _run(xs, minimum_short_excursion_frames=2)
    assert result.stride_diagnostic.sensitive
    assert result.temporal_support_status is TemporalSupportStatus.STRIDE_SENSITIVE
    assert result.evidence_pattern is TemporalEvidencePattern.SHORT_EXCURSION_ONLY


def test_ensemble_retains_membership_but_has_no_temporal_continuity():
    _, _, _, result = _run([0.2, 0.3, 0.7, 0.6], semantics="ensemble")
    assert result.temporal_support_status is TemporalSupportStatus.UNAVAILABLE
    assert result.evidence_pattern is TemporalEvidencePattern.ENSEMBLE_UNAVAILABLE
    assert result.residences == () and result.passages == () and result.core_visits == ()
    assert np.any(result.membership.raw_classification == RawMembershipClass.CORE)



def test_segment_reset_prevents_a_cross_segment_jump_claim():
    xs = np.r_[_jitter(0.2, 8), _jitter(0.7, 8)]
    catalog = _sample_catalog(xs, segment_starts=(8,))
    estimate, attractors = _density_and_attractors(catalog)
    result = prepare_provisional_temporal_assignment(
        catalog,
        estimate,
        attractors,
        options=TemporalAssignmentOptions(minimum_decorrelation_samples=6),
    )
    assert len(result.residences) == 2
    assert {item.segment_id for item in result.residences} == {0, 1}
    assert result.passages == ()
    assert result.evidence_pattern is TemporalEvidencePattern.SINGLE_STATE


def test_irregular_time_stride_retains_only_a_frame_domain_decorrelation_claim():
    xs = _jitter(0.2, 16)
    times = np.cumsum(np.r_[0.0, np.resize([0.1, 0.2], 15)])
    catalog = _sample_catalog(xs, times=times)
    estimate, attractors = _density_and_attractors(catalog)
    result = prepare_provisional_temporal_assignment(
        catalog,
        estimate,
        attractors,
        options=TemporalAssignmentOptions(
            minimum_decorrelation_samples=6,
            maximum_relative_stride_deviation=0.05,
        ),
    )
    local = result.decorrelation_estimates[0]
    assert local.status is DecorrelationStatus.FRAME_ONLY_IRREGULAR_STRIDE
    assert local.decorrelation_time_frames is not None
    assert local.decorrelation_time is None


def test_cross_catalog_source_binding_fails_before_temporal_work():
    catalog_a = _sample_catalog(_jitter(0.2, 8))
    estimate_a, attractors_a = _density_and_attractors(catalog_a)
    catalog_b = _sample_catalog(_jitter(0.7, 8))
    with pytest.raises(TemporalAssignmentInputError):
        prepare_provisional_temporal_assignment(catalog_b, estimate_a, attractors_a)

def test_serialization_tamper_rejection_resources_and_public_exports():
    xs = np.r_[_jitter(0.2, 8), [0.45, 0.60], _jitter(0.7, 8)]
    catalog, estimate, attractors, result = _run(xs)
    replay = type(result).from_dict(result.to_dict())
    assert replay.signature == result.signature
    payload = copy.deepcopy(result.to_dict())
    payload["membership"]["basin_membership"][0] = 99
    with pytest.raises(TemporalAssignmentInputError):
        type(result).from_dict(payload)
    with pytest.raises(TemporalAssignmentResourceError):
        prepare_provisional_temporal_assignment(
            catalog,
            estimate,
            attractors,
            resources=TemporalAssignmentResourcePolicy(max_samples=1),
        )
    for name in (
        "ProvisionalTemporalAssignmentCatalog",
        "TemporalAssignmentOptions",
        "TemporalEvidencePattern",
        "prepare_provisional_temporal_assignment",
    ):
        assert hasattr(mdstats, name)


def test_coordinate_identical_partition_transfer_allows_only_weight_change():
    from dataclasses import replace

    discovery = _sample_catalog(np.r_[_jitter(0.2, 8), _jitter(0.7, 8)])
    estimate, attractors = _density_and_attractors(discovery)
    weights = np.asarray(discovery.represented_time_weights, dtype=float).copy()
    weights[::2] *= 0.5
    assignment = replace(discovery, represented_time_weights=weights, signature="")
    result = prepare_provisional_temporal_assignment(
        assignment,
        estimate,
        attractors,
        discovery_catalog=discovery,
        options=TemporalAssignmentOptions(
            minimum_decorrelation_samples=4,
            maximum_autocorrelation_lag=8,
            stride_factors=(1, 2),
        ),
    )
    assert result.metadata["partition_transfer_performed"] is True
    assert result.metadata["partition_transfer_identity"] == "exact_registered_coordinate_identity"
    assert result.metadata["partition_discovery_catalog_signature"] == discovery.signature
    assert result.metadata["partition_assignment_catalog_signature"] == assignment.signature


def test_partition_transfer_rejects_registered_coordinate_mismatch():
    from dataclasses import replace

    discovery = _sample_catalog(np.r_[_jitter(0.2, 8), _jitter(0.7, 8)])
    estimate, attractors = _density_and_attractors(discovery)
    positions = np.asarray(discovery.registered_positions, dtype=float).copy()
    positions[0, 0] += 1.0e-12
    assignment = replace(discovery, registered_positions=positions, signature="")
    with pytest.raises(TemporalAssignmentInputError, match="exact source, registration, topology, atom, frame, and registered-coordinate identity"):
        prepare_provisional_temporal_assignment(
            assignment,
            estimate,
            attractors,
            discovery_catalog=discovery,
        )
