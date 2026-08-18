from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats.analysis.natural_tiling as natural_tiling_module
from mdstats.analysis import (
    CandidateEligibility,
    CertificationState,
    EdgeIncidencePlacementDomain,
    FaceCompatibilityConstraintSystem,
    FaceWitnessAssignment,
    NaturalTilingCandidate,
    NaturalTilingCertification,
    NaturalTilingInputError,
    NaturalTilingOutcomeKind,
    NaturalTilingResourceError,
    NaturalTilingSymmetryResources,
    PropernessStatus,
    RingPlacement,
    RingStrengthCatalog,
    RingStrengthDiagnostics,
    RingStrengthDomain,
    RingStrengthResources,
    RingStrengthResult,
    RingStrengthStatus,
    RingStrengthWitness,
    build_natural_tiling_catalog,
    build_periodic_cell_complex_symmetry_action,
    certify_natural_tiling_candidate,
    certify_periodic_tetrahedral_partition,
    discover_periodic_net_symmetry,
)
from tests.test_periodic_cell_complex import _simple_cubic_fixture

ZERO = (0, 0, 0)


def _compatibility(fixture):
    assignments = tuple(
        FaceWitnessAssignment(
            certificate.face_placement.digest,
            witness.witness_id,
            witness.digest,
        )
        for certificate, witness in zip(
            fixture.face_certificates, fixture.witnesses, strict=True
        )
    )
    return FaceCompatibilityConstraintSystem(
        tuple(certificate.digest for certificate in fixture.face_certificates),
        assignments,
        (),
        (),
    )


def _strength_catalog(fixture, *, weak_index=None):
    results = []
    for index, ring in enumerate(fixture.ring_index.catalog.rings):
        placement = RingPlacement(
            fixture.ring_index.topology_graph_digest, ring.key, ZERO
        )
        status = (
            RingStrengthStatus.WEAK_CERTIFIED
            if index == weak_index
            else RingStrengthStatus.STRONG_IN_DOMAIN
        )
        witness = None
        if status is RingStrengthStatus.WEAK_CERTIFIED:
            component = fixture.ring_index.catalog.rings[(index + 1) % 3]
            witness = RingStrengthWitness(
                placement,
                (
                    RingPlacement(
                        fixture.ring_index.topology_graph_digest,
                        component.key,
                        ZERO,
                    ),
                ),
            )
        results.append(
            RingStrengthResult(
                topology_graph_digest=fixture.ring_index.topology_graph_digest,
                primitive_ring_catalog_digest=fixture.ring_index.catalog_digest,
                target_placement=placement,
                domain=RingStrengthDomain(
                    ring.key,
                    3,
                    EdgeIncidencePlacementDomain(1),
                ),
                resources=RingStrengthResources(),
                status=status,
                diagnostics=RingStrengthDiagnostics(
                    source_complete=True,
                    source_issue=None,
                    admitted_ring_key_count=3,
                    candidate_placement_count=3,
                    explored_edge_instance_count=3,
                    support_term_count=12,
                    achieved_incidence_depth=1,
                    requested_incidence_depth=1,
                    truncation_reason=None,
                ),
                candidate_set_digest=(f"{index + 1:x}" * 64)[:64],
                witness=witness,
            )
        )
    return RingStrengthCatalog(
        fixture.ring_index.topology_graph_digest,
        fixture.ring_index.catalog_digest,
        tuple(results),
    )


def _complete_fixture():
    fixture = _simple_cubic_fixture()
    discovery = discover_periodic_net_symmetry(
        fixture.view, ring_index=fixture.ring_index
    )
    partition = certify_periodic_tetrahedral_partition(
        fixture.complex,
        fixture.embedding,
        fixture.ring_index,
        fixture.witnesses,
        fixture.auxiliary_vertices,
        fixture.tetrahedra,
    )
    return fixture, discovery, partition


def test_full_cubic_group_preserves_scientific_faces_tiles_and_group_action():
    fixture, discovery, _partition = _complete_fixture()
    action = build_periodic_cell_complex_symmetry_action(
        fixture.complex, discovery.symmetry, discovery.ring_symmetry
    )
    assert action.preserved
    assert len(action.operation_results) == 48
    assert action.composition_check_count == 48 * 48 * 4
    assert all(len(row.face_images) == 3 for row in action.operation_results)
    assert all(len(row.tile_images) == 1 for row in action.operation_results)
    assert any(
        image.orientation == -1
        for row in action.operation_results
        for image in row.tile_images
    )


def test_scientific_action_ignores_auxiliary_partition_mesh_identity():
    fixture, discovery, partition = _complete_fixture()
    action = build_periodic_cell_complex_symmetry_action(
        fixture.complex, discovery.symmetry, discovery.ring_symmetry
    )
    assert partition.digest not in action.to_dict().values()
    assert "tetrahedra" not in str(action.to_dict())


def test_missing_scientific_face_image_certifies_nonpreservation(monkeypatch):
    fixture, discovery, _partition = _complete_fixture()
    original = natural_tiling_module._face_images_for_operation

    def missing(complex_, symmetry, ring_symmetry, operation_index):
        if operation_index == 1:
            return None
        return original(complex_, symmetry, ring_symmetry, operation_index)

    monkeypatch.setattr(natural_tiling_module, "_face_images_for_operation", missing)
    action = build_periodic_cell_complex_symmetry_action(
        fixture.complex, discovery.symmetry, discovery.ring_symmetry
    )
    assert not action.preserved
    assert action.failed_operation_indices == (1,)
    assert action.composition_check_count == 0


def test_action_resource_preflight_is_transactional():
    fixture, discovery, _partition = _complete_fixture()
    with pytest.raises(NaturalTilingResourceError, match="Face-image"):
        build_periodic_cell_complex_symmetry_action(
            fixture.complex,
            discovery.symmetry,
            discovery.ring_symmetry,
            resources=NaturalTilingSymmetryResources(
                max_operation_face_images=1,
                max_operation_tile_images=1_000,
                max_composition_checks=100_000,
            ),
        )


def test_complete_candidate_is_eligible_proper_and_unique():
    fixture, discovery, partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        _compatibility(fixture),
        fixture.complex,
        partition,
    )
    assert candidate.eligibility is CandidateEligibility.ELIGIBLE
    assert candidate.certification.properness is PropernessStatus.CERTIFIED_PROPER
    assert candidate.certification.strength_complete is CertificationState.CERTIFIED
    catalog = build_natural_tiling_catalog((candidate,))
    assert catalog.outcome.kind is NaturalTilingOutcomeKind.UNIQUE
    assert catalog.essential_ring_keys == candidate.selected_ring_keys


def test_missing_partition_and_compatibility_remain_explicitly_unresolved():
    fixture, discovery, _partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        None,
        fixture.complex,
        None,
    )
    assert candidate.eligibility is CandidateEligibility.UNRESOLVED
    assert candidate.certification.partition_certified is CertificationState.UNRESOLVED
    assert candidate.certification.compatibility_complete is CertificationState.UNRESOLVED
    catalog = build_natural_tiling_catalog((candidate,))
    assert catalog.outcome.kind is NaturalTilingOutcomeKind.NONE
    assert catalog.unresolved_candidates == (candidate,)
    assert catalog.essential_ring_keys == ()


def test_certified_weak_selected_face_rejects_candidate():
    fixture, discovery, partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture, weak_index=0),
        fixture.face_certificates,
        fixture.witnesses,
        _compatibility(fixture),
        fixture.complex,
        partition,
    )
    assert candidate.eligibility is CandidateEligibility.INELIGIBLE
    assert candidate.certification.strength_complete is CertificationState.REJECTED
    assert candidate.certification.rejection_reasons


def test_same_scientific_complex_deduplicates_different_auxiliary_evidence():
    fixture, discovery, partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        _compatibility(fixture),
        fixture.complex,
        partition,
    )
    duplicate = replace(candidate, partition_certificate_digest="f" * 64, evidence_digest="")
    assert duplicate.digest == candidate.digest
    assert duplicate.evidence_digest != candidate.evidence_digest
    catalog = build_natural_tiling_catalog((duplicate, candidate))
    assert len(catalog.candidates) == 1
    assert catalog.outcome.kind is NaturalTilingOutcomeKind.UNIQUE


def test_multiple_eligible_scientific_identities_remain_explicit():
    fixture, discovery, partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        _compatibility(fixture),
        fixture.complex,
        partition,
    )
    alternative = replace(
        candidate,
        periodic_cell_complex_digest="e" * 64,
        digest="",
        evidence_digest="",
    )
    catalog = build_natural_tiling_catalog((alternative, candidate))
    assert catalog.outcome.kind is NaturalTilingOutcomeKind.MULTIPLE
    assert len(catalog.eligible_candidates) == 2


def test_candidate_digest_rejects_tampering():
    fixture, discovery, partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        _compatibility(fixture),
        fixture.complex,
        partition,
    )
    with pytest.raises(NaturalTilingInputError, match="scientific candidate digest"):
        replace(candidate, periodic_cell_complex_digest="d" * 64)


def test_catalog_rejects_conflicting_eligible_and_ineligible_evidence():
    fixture, discovery, partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        _compatibility(fixture),
        fixture.complex,
        partition,
    )
    rejected_certification = NaturalTilingCertification(
        primitive_ring_bound=4,
        primitive_complete=CertificationState.CERTIFIED,
        symmetry_complete=CertificationState.CERTIFIED,
        strength_complete=CertificationState.REJECTED,
        embedding_complete=CertificationState.CERTIFIED,
        compatibility_complete=CertificationState.CERTIFIED,
        cell_complex_valid=CertificationState.CERTIFIED,
        partition_certified=CertificationState.CERTIFIED,
        properness=PropernessStatus.CERTIFIED_PROPER,
        rejection_reasons=("fixture rejection",),
    )
    rejected = replace(
        candidate,
        certification=rejected_certification,
        evidence_digest="",
    )
    with pytest.raises(NaturalTilingInputError, match="Conflicting"):
        build_natural_tiling_catalog((candidate, rejected))


def test_empty_catalog_represents_certified_no_accepted_candidate_domain():
    fixture = _simple_cubic_fixture()
    catalog = build_natural_tiling_catalog(
        (),
        periodic_net_view_digest=fixture.view.digest,
        primitive_ring_catalog_digest=fixture.ring_index.catalog_digest,
    )
    assert catalog.outcome.kind is NaturalTilingOutcomeKind.NONE
    assert catalog.candidates == ()
    assert catalog.essential_ring_keys == ()


def test_candidate_and_catalog_serialization_round_trip():
    fixture, discovery, partition = _complete_fixture()
    candidate = certify_natural_tiling_candidate(
        fixture.view,
        discovery,
        fixture.ring_index,
        _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        _compatibility(fixture),
        fixture.complex,
        partition,
    )
    restored_candidate = NaturalTilingCandidate.from_dict(candidate.to_dict())
    assert restored_candidate == candidate
    assert restored_candidate.to_dict() == candidate.to_dict()
    catalog = build_natural_tiling_catalog((candidate,))
    restored_catalog = type(catalog).from_dict(catalog.to_dict())
    assert restored_catalog == catalog
    assert restored_catalog.to_dict() == catalog.to_dict()


def test_cell_complex_symmetry_action_source_replay_rejects_tampering():
    fixture, discovery, _partition = _complete_fixture()
    action = build_periodic_cell_complex_symmetry_action(
        fixture.complex, discovery.symmetry, discovery.ring_symmetry
    )
    restored = type(action).from_dict(
        action.to_dict(),
        complex_=fixture.complex,
        symmetry=discovery.symmetry,
        ring_symmetry=discovery.ring_symmetry,
    )
    assert restored == action
    payload = action.to_dict()
    payload["operation_results"][0]["face_images"][0]["image_shift"] = [99, 0, 0]
    with pytest.raises(Exception, match="not canonical"):
        type(action).from_dict(
            payload,
            complex_=fixture.complex,
            symmetry=discovery.symmetry,
            ring_symmetry=discovery.ring_symmetry,
        )
