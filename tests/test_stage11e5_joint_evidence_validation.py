from __future__ import annotations

import copy
from dataclasses import replace

import numpy as np
import pytest

import mdstats
from mdstats.analysis import (
    RegisteredStructuralFrameStatus,
    RegisteredStructuralFrameView,
    RegisteredStructuralGeometryView,
    RegisteredStructuralViewOptions,
    RegisteredStructuralViewResources,
    RegisteredTileCageEmbedding,
)
from mdstats.analysis.density import (
    EvidenceBlockPlan,
    EvidenceChannelStatus,
    ExchangeabilityStatus,
    FinalValidationStatus,
    JointEvidenceInputError,
    JointEvidenceOptions,
    JointEvidenceResourceError,
    JointEvidenceResourcePolicy,
    OverallCertificationStatus,
    StructuralAssociationStatus,
    SymmetryOrbitCandidate,
    TemporalAssignmentOptions,
    ValidatedFrozenCatalog,
    prepare_final_refit_catalog,
    prepare_provisional_temporal_assignment,
    prepare_validated_frozen_catalog,
)

from tests.test_stage11e3_force_refinement import _pipeline, _run as _force_run
from tests.test_stage11e4_temporal_assignment import _density_and_attractors, _sample_catalog


def _structural_view(catalog, centers):
    tiles = []
    for index, center in enumerate(centers):
        c = tuple(float(v) for v in center)
        tiles.append(
            RegisteredTileCageEmbedding(
                tile_index=index,
                physical_center=c,
                registered_center=c,
                registered_fractional_unwrapped=c,
                registered_fractional_wrapped=tuple(float(v % 1.0) for v in c),
                registered_image_shift=(0, 0, 0),
                physical_volume=1.0,
                physical_surface_area=6.0,
                physical_equivalent_sphere_radius=0.62,
                physical_sphericity=0.8,
                physical_diameter=1.5,
                physical_orientation_preserved=True,
            )
        )
    frame = RegisteredStructuralFrameView(
        result_position=0,
        collection_frame_index=0,
        frame_id=int(np.min(catalog.frame_ids)),
        status=RegisteredStructuralFrameStatus.RESOLVED,
        registered_cell=tuple(tuple(float(v) for v in row) for row in np.eye(3)),
        rings=(),
        tiles=tuple(tiles),
        tile_faces=(),
        windows=(),
        diagnostics=(),
    )
    return RegisteredStructuralGeometryView(
        collection_binding_digest="a" * 64,
        registration_signature=catalog.registration_signature,
        frame_ring_geometry_digest="b" * 64,
        ring_boundary_digest="c" * 64,
        frame_tiling_geometry_digest="d" * 64,
        options=RegisteredStructuralViewOptions(),
        resources=RegisteredStructuralViewResources(),
        frames=(frame,),
    )


def _one_state(*, force=False):
    catalog, estimate, attractors = _pipeline(force=force, pmf=force)
    temporal = prepare_provisional_temporal_assignment(
        catalog,
        estimate,
        attractors,
        force_refinement=None,
        options=TemporalAssignmentOptions(
            minimum_decorrelation_samples=6,
            maximum_autocorrelation_lag=16,
            minimum_persistence_tau_multiples=1.0,
        ),
    )
    force_catalog = _force_run(catalog, estimate, attractors) if force else None
    structural = _structural_view(catalog, ((0.5, 0.5, 0.5),))
    plan = EvidenceBlockPlan(tuple(range(0, 24)), tuple(range(24, 48)), tuple(range(48, 72)))
    return catalog, estimate, attractors, temporal, force_catalog, structural, plan


def _two_state():
    xs = np.concatenate((np.full(12, 0.20), np.linspace(0.20, 0.70, 4), np.full(12, 0.70)))
    catalog = _sample_catalog(xs)
    estimate, attractors = _density_and_attractors(catalog)
    temporal = prepare_provisional_temporal_assignment(
        catalog,
        estimate,
        attractors,
        options=TemporalAssignmentOptions(
            minimum_decorrelation_samples=6,
            maximum_autocorrelation_lag=16,
            minimum_persistence_tau_multiples=1.0,
        ),
    )
    structural = _structural_view(catalog, ((0.20, 0.0, 0.0), (0.70, 0.0, 0.0)))
    return catalog, estimate, attractors, temporal, structural


def test_force_free_site_is_spatial_temporal_but_not_force_validated():
    catalog, estimate, attractors, temporal, force, structural, plan = _one_state(force=False)
    result = prepare_validated_frozen_catalog(
        catalog, estimate, attractors, temporal, structural, force_refinement=force, block_plan=plan
    )
    state = result.states[0]
    assert state.evidence.temporal is EvidenceChannelStatus.RESOLVED
    assert state.evidence.force is EvidenceChannelStatus.UNAVAILABLE
    assert state.evidence.overall is OverallCertificationStatus.SPATIAL_TEMPORAL_VALIDATED
    assert state.evidence.final_validation is FinalValidationStatus.INDEPENDENT_VALIDATION_SUPPORTED
    assert state.structural_association.status is StructuralAssociationStatus.RESOLVED
    assert result.metadata["nearest_structural_object_fallback_performed"] is False


def test_force_validated_state_uses_score_covector_and_reaches_full_validation():
    catalog, estimate, attractors, temporal, force, structural, plan = _one_state(force=True)
    result = prepare_validated_frozen_catalog(
        catalog, estimate, attractors, temporal, structural, force_refinement=force, block_plan=plan
    )
    state = result.states[0]
    assert state.evidence.force is EvidenceChannelStatus.RESOLVED
    assert state.evidence.force_score_consistency is EvidenceChannelStatus.RESOLVED
    assert state.evidence.curvature is EvidenceChannelStatus.RESOLVED
    assert state.evidence.overall is OverallCertificationStatus.FULLY_VALIDATED
    assert result.metadata["force_compared_to_density_score_covector"] is True
    assert result.metadata["force_compared_to_unqualified_gradient"] is False


def test_force_score_disagreement_remains_explicit():
    catalog, estimate, attractors, temporal, force, structural, plan = _one_state(force=True)
    altered_refinement = replace(force.refinements[0], density_force_residual_norm=9.0, signature="")
    altered_force = replace(force, refinements=(altered_refinement,), signature="")
    result = prepare_validated_frozen_catalog(
        catalog, estimate, attractors, temporal, structural,
        force_refinement=altered_force, block_plan=plan,
        options=JointEvidenceOptions(force_score_residual_tolerance=0.5),
    )
    state = result.states[0]
    assert state.evidence.force is EvidenceChannelStatus.RESOLVED
    assert state.evidence.force_score_consistency is EvidenceChannelStatus.DISAGREEMENT
    assert state.evidence.overall is OverallCertificationStatus.EVIDENCE_DISAGREEMENT
    assert "matched_force_disagrees_with_density_score_covector" in state.evidence.diagnostics


def test_ambiguous_association_is_retained_without_nearest_fallback():
    catalog, estimate, attractors, temporal, _force, _structural, plan = _one_state(force=False)
    structural = _structural_view(catalog, ((0.45, 0.5, 0.5), (0.55, 0.5, 0.5)))
    result = prepare_validated_frozen_catalog(
        catalog, estimate, attractors, temporal, structural, block_plan=plan,
        options=JointEvidenceOptions(maximum_association_distance=0.3, association_ambiguity_distance=0.05),
    )
    association = result.states[0].structural_association
    assert association.status is StructuralAssociationStatus.AMBIGUOUS
    assert association.primary is None
    assert len(association.candidates) == 2
    assert result.structural_complexes == ()


def test_no_object_inside_declared_radius_stays_unresolved():
    catalog, estimate, attractors, temporal, _force, _structural, plan = _one_state(force=False)
    structural = _structural_view(catalog, ((0.8, 0.8, 0.8),))
    result = prepare_validated_frozen_catalog(
        catalog, estimate, attractors, temporal, structural, block_plan=plan,
        options=JointEvidenceOptions(maximum_association_distance=0.1, association_ambiguity_distance=0.01),
    )
    association = result.states[0].structural_association
    assert association.status is StructuralAssociationStatus.UNRESOLVED
    assert association.candidates == ()
    assert association.diagnostic == "no_structural_object_within_declared_association_distance"


def test_one_transition_early_late_split_is_not_rejected():
    catalog, estimate, attractors, temporal, structural = _two_state()
    plan = EvidenceBlockPlan(tuple(range(0, 8)), tuple(range(8, 14)), tuple(range(20, 28)))
    result = prepare_validated_frozen_catalog(
        catalog, estimate, attractors, temporal, structural, block_plan=plan,
        options=JointEvidenceOptions(minimum_block_samples=2, maximum_transfer_fraction_shift=0.2),
    )
    assert {s.evidence.final_validation for s in result.states} == {FinalValidationStatus.INSUFFICIENT_TRANSFER_SUPPORT}
    assert all(s.evidence.overall is not OverallCertificationStatus.REJECTED for s in result.states)


def test_symmetry_grouping_is_opt_in_and_exchangeability_precedes_orbit_status():
    catalog, estimate, attractors, temporal, structural = _two_state()
    base = prepare_validated_frozen_catalog(catalog, estimate, attractors, temporal, structural)
    assert base.symmetry_orbits == ()
    candidate = SymmetryOrbitCandidate("nominal-pair", (0, 1), 2, "synthetic structural symmetry")
    result = prepare_validated_frozen_catalog(
        catalog, estimate, attractors, temporal, structural,
        symmetry_orbit_candidates=(candidate,),
    )
    orbit = result.symmetry_orbits[0]
    assert orbit.status in {ExchangeabilityStatus.INSUFFICIENT, ExchangeabilityStatus.REJECTED}
    assert orbit.augmentation_performed is False
    assert "force_exchangeability_unavailable" in orbit.reasons


def test_selection_conditioned_and_unavailable_validation_are_explicit():
    catalog, estimate, attractors, temporal, _force, structural, _plan = _one_state(force=False)
    conditioned = EvidenceBlockPlan(tuple(range(0, 36)), tuple(range(36, 60)), tuple(range(48, 72)))
    result = prepare_validated_frozen_catalog(catalog, estimate, attractors, temporal, structural, block_plan=conditioned)
    assert result.states[0].evidence.final_validation is FinalValidationStatus.SELECTION_CONDITIONED
    unavailable = prepare_validated_frozen_catalog(catalog, estimate, attractors, temporal, structural)
    assert unavailable.states[0].evidence.final_validation is FinalValidationStatus.INDEPENDENT_VALIDATION_UNAVAILABLE


def test_final_refit_is_distinct_and_does_not_inherit_parameter_validation():
    catalog, estimate, attractors, temporal, _force, structural, plan = _one_state(force=False)
    frozen = prepare_validated_frozen_catalog(catalog, estimate, attractors, temporal, structural, block_plan=plan)
    refit = prepare_final_refit_catalog(frozen, attractors)
    assert refit.validated_frozen_catalog_signature == frozen.signature
    assert refit.decision_inherited is True
    assert refit.parameter_validation_inherited is False
    assert refit.refit_attractor_catalog_signature == attractors.signature


def test_serialization_tamper_resources_source_binding_and_public_api():
    catalog, estimate, attractors, temporal, _force, structural, plan = _one_state(force=False)
    result = prepare_validated_frozen_catalog(catalog, estimate, attractors, temporal, structural, block_plan=plan)
    replay = ValidatedFrozenCatalog.from_dict(result.to_dict())
    assert replay.signature == result.signature
    payload = copy.deepcopy(result.to_dict())
    payload["states"][0]["evidence"]["overall"] = OverallCertificationStatus.FULLY_VALIDATED.value
    with pytest.raises(JointEvidenceInputError):
        ValidatedFrozenCatalog.from_dict(payload)
    with pytest.raises(JointEvidenceResourceError):
        prepare_validated_frozen_catalog(
            catalog, estimate, attractors, temporal, structural,
            resources=JointEvidenceResourcePolicy(max_states=1, max_structural_candidates=1, max_block_memberships=1),
        )
    wrong_view = replace(structural, registration_signature="f" * 64, digest="")
    with pytest.raises(JointEvidenceInputError):
        prepare_validated_frozen_catalog(catalog, estimate, attractors, temporal, wrong_view)
    assert mdstats.JOINT_EVIDENCE_STAGE == "11E5"
    assert mdstats.prepare_validated_frozen_catalog is prepare_validated_frozen_catalog
