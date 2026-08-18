from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from mdstats.analysis import (
    CandidateEligibility,
    FaceCompatibilityConstraint,
    FaceCompatibilityConstraintSystem,
    FaceConstraintKind,
    FaceEmbeddingWitness,
    FacePlacementCertificate,
    FacePlacementStatus,
    FaceWitnessMethod,
    NaturalFaceOrbitStrength,
    NaturalFaceSelection,
    NaturalTilingOutcomeKind,
    NaturalTilingSearchInputError,
    NaturalTilingSearchRejectionKind,
    NaturalTilingSearchResourceError,
    NaturalTilingSearchResources,
    NaturalTilingSearchResult,
    NaturalTilingSearchSerializationError,
    NaturalTilingSearchStatus,
    RingPlacement,
    RingStrengthCatalog,
    RingStrengthStatus,
    build_periodic_cell_complex,
    certify_periodic_tetrahedral_partition,
    discover_periodic_net_symmetry,
    make_face_placement,
    maximal_face_selections,
    search_natural_tilings_from_master_refinement,
)
from tests.test_natural_tiling import _compatibility, _strength_catalog
from tests.test_periodic_cell_complex import _simple_cubic_fixture

ZERO = (0, 0, 0)


def _reduced_symmetry_fixture():
    """Simple cubic net with axis labels suppressing coordinate permutations."""

    source = _simple_cubic_fixture()
    view = replace(
        source.view,
        edge_signatures=(("axis-x",), ("axis-y",), ("axis-z",)),
        digest="",
    )
    embedding = replace(
        source.embedding,
        periodic_net_view_digest=view.digest,
        digest="",
    )
    certificates = []
    witnesses = []
    for old_certificate, old_witness in zip(
        source.face_certificates, source.witnesses, strict=True
    ):
        face = make_face_placement(
            embedding,
            source.ring_index,
            RingPlacement(
                source.ring_index.topology_graph_digest,
                old_certificate.face_placement.ring_placement.ring_key,
                ZERO,
            ),
        )
        witness = FaceEmbeddingWitness(
            face,
            old_witness.witness_id,
            FaceWitnessMethod.BOUNDARY_VERTEX_TRIANGULATION,
            old_witness.triangles,
            old_witness.periodic_self_candidate_set_digest,
            old_witness.framework_candidate_set_digest,
            (),
        )
        certificate = FacePlacementCertificate(
            view.digest,
            view.source_graph_digest,
            embedding.digest,
            source.ring_index.catalog_digest,
            old_certificate.periodic_edge_intersection_certificate_digest,
            face,
            1,
            (witness,),
            (),
            FacePlacementStatus.CERTIFIED_ADMISSIBLE,
        )
        certificates.append(certificate)
        witnesses.append(witness)
    complex_ = build_periodic_cell_complex(
        view,
        embedding,
        source.ring_index,
        certificates,
        witnesses,
        (source.shell,),
    )
    partition = certify_periodic_tetrahedral_partition(
        complex_,
        embedding,
        source.ring_index,
        witnesses,
        source.auxiliary_vertices,
        source.tetrahedra,
    )
    discovery = discover_periodic_net_symmetry(view, ring_index=source.ring_index)
    return SimpleNamespace(
        view=view,
        embedding=embedding,
        ring_index=source.ring_index,
        face_certificates=tuple(certificates),
        witnesses=tuple(witnesses),
        complex=complex_,
        partition=partition,
        discovery=discovery,
    )


def _search(fixture, *, strength=None, compatibility=None, resources=None):
    return search_natural_tilings_from_master_refinement(
        fixture.view,
        fixture.discovery,
        fixture.embedding,
        fixture.ring_index,
        strength or _strength_catalog(fixture),
        fixture.face_certificates,
        fixture.witnesses,
        compatibility or _compatibility(fixture),
        fixture.complex,
        fixture.partition,
        resources=resources,
    )


def _unresolved_strength_catalog(fixture, index=0):
    base = _strength_catalog(fixture)
    result = base.results[index]
    unresolved = replace(
        result,
        status=RingStrengthStatus.UNRESOLVED_TRUNCATED,
        diagnostics=replace(
            result.diagnostics,
            truncation_reason="fixture search bound",
        ),
        witness=None,
        digest="",
    )
    results = list(base.results)
    results[index] = unresolved
    return RingStrengthCatalog(
        base.topology_graph_digest,
        base.primitive_ring_catalog_digest,
        tuple(results),
    )


def test_full_cubic_master_search_is_one_symmetry_orbit_and_unique():
    source = _simple_cubic_fixture()
    discovery = discover_periodic_net_symmetry(
        source.view, ring_index=source.ring_index
    )
    partition = certify_periodic_tetrahedral_partition(
        source.complex,
        source.embedding,
        source.ring_index,
        source.witnesses,
        source.auxiliary_vertices,
        source.tetrahedra,
    )
    fixture = SimpleNamespace(
        **source.__dict__, discovery=discovery, partition=partition
    )
    result = _search(fixture)
    assert result.status is NaturalTilingSearchStatus.COMPLETE
    assert result.search_complete
    assert result.certified_catalog is result.catalog
    assert result.attempted_selection_count == 1
    assert result.compatible_selection_count == 1
    assert result.constructed_selection_count == 1
    assert len(result.face_orbits) == 1
    assert result.face_orbits[0].face_indices == (0, 1, 2)
    assert result.face_orbits[0].strength is NaturalFaceOrbitStrength.STRONG_SELECTABLE
    assert len(result.candidates) == 1
    assert result.candidates[0].natural_tiling_candidate.eligibility is CandidateEligibility.ELIGIBLE
    assert result.catalog.outcome.kind is NaturalTilingOutcomeKind.UNIQUE
    assert result.candidates[0].cell_complex.cell_counts == (1, 3, 3, 1)
    assert result.candidates[0].partition_certificate.total_fractional_volume == 1


def test_axis_labeled_search_enumerates_all_orbit_subsets_and_rejects_periodic_slabs():
    fixture = _reduced_symmetry_fixture()
    assert fixture.discovery.symmetry.order == 8
    assert fixture.discovery.ring_symmetry.ring_orbits == ((0,), (1,), (2,))
    result = _search(fixture)
    assert result.attempted_selection_count == 7
    assert result.compatible_selection_count == 7
    assert result.constructed_selection_count == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].selection.selected_orbit_indices == (0, 1, 2)
    noncompact = [
        value
        for value in result.rejections
        if value.kind is NaturalTilingSearchRejectionKind.NONCOMPACT_TILE_COMPONENT
    ]
    assert len(noncompact) == 6
    assert result.catalog.outcome.kind is NaturalTilingOutcomeKind.UNIQUE


def test_certified_weak_orbit_is_excluded_before_selection_enumeration():
    fixture = _reduced_symmetry_fixture()
    result = _search(fixture, strength=_strength_catalog(fixture, weak_index=0))
    assert result.face_orbits[0].strength is NaturalFaceOrbitStrength.WEAK_EXCLUDED
    assert result.attempted_selection_count == 3
    assert result.constructed_selection_count == 0
    assert result.status is NaturalTilingSearchStatus.COMPLETE
    assert result.catalog.outcome.kind is NaturalTilingOutcomeKind.NONE


def test_unresolved_strength_keeps_search_and_catalog_conditional():
    fixture = _reduced_symmetry_fixture()
    result = _search(fixture, strength=_unresolved_strength_catalog(fixture))
    assert result.face_orbits[0].strength is NaturalFaceOrbitStrength.UNRESOLVED
    assert result.status is NaturalTilingSearchStatus.UNRESOLVED
    assert not result.search_complete
    assert result.certified_catalog is None
    assert result.unresolved_reasons


def test_higher_order_crossing_constraint_prunes_the_only_closed_selection():
    fixture = _reduced_symmetry_fixture()
    compatibility = _compatibility(fixture)
    forbidden = FaceCompatibilityConstraint(
        FaceConstraintKind.HIGHER_ORDER_FORBIDDEN,
        compatibility.assignments,
        "fixture crossing alternative",
    )
    constrained = FaceCompatibilityConstraintSystem(
        compatibility.face_certificate_digests,
        compatibility.assignments,
        compatibility.pair_certificates,
        (forbidden,),
    )
    result = _search(fixture, compatibility=constrained)
    assert result.constructed_selection_count == 0
    assert result.catalog.outcome.kind is NaturalTilingOutcomeKind.NONE
    assert any(
        value.kind is NaturalTilingSearchRejectionKind.FORBIDDEN_COMPATIBILITY
        and value.selected_orbit_indices == (0, 1, 2)
        for value in result.rejections
    )


def test_unresolved_crossing_constraint_is_not_converted_to_rejection():
    fixture = _reduced_symmetry_fixture()
    compatibility = _compatibility(fixture)
    unresolved = FaceCompatibilityConstraint(
        FaceConstraintKind.UNRESOLVED,
        compatibility.assignments,
        "fixture unresolved crossing",
    )
    constrained = FaceCompatibilityConstraintSystem(
        compatibility.face_certificate_digests,
        compatibility.assignments,
        compatibility.pair_certificates,
        (unresolved,),
    )
    result = _search(fixture, compatibility=constrained)
    assert result.status is NaturalTilingSearchStatus.UNRESOLVED
    assert result.catalog.outcome.kind is NaturalTilingOutcomeKind.NONE
    assert any(
        value.kind is NaturalTilingSearchRejectionKind.UNRESOLVED_COMPATIBILITY
        for value in result.rejections
    )


def test_selection_family_resource_preflight_is_transactional():
    fixture = _reduced_symmetry_fixture()
    with pytest.raises(NaturalTilingSearchResourceError, match="max_face_selections"):
        _search(
            fixture,
            resources=NaturalTilingSearchResources(max_face_selections=6),
        )


def test_master_witness_binding_rejects_reordered_evidence():
    fixture = _reduced_symmetry_fixture()
    with pytest.raises(NaturalTilingSearchInputError, match="Master witnesses"):
        search_natural_tilings_from_master_refinement(
            fixture.view,
            fixture.discovery,
            fixture.embedding,
            fixture.ring_index,
            _strength_catalog(fixture),
            fixture.face_certificates,
            tuple(reversed(fixture.witnesses)),
            _compatibility(fixture),
            fixture.complex,
            fixture.partition,
        )


def test_maximal_selection_filter_preserves_incomparable_crossing_alternatives():
    a = "a" * 64
    b = "b" * 64
    c = "c" * 64
    u = "d" * 64
    v = "e" * 64
    w = "f" * 64
    left = NaturalFaceSelection((0, 1), (0, 1), (a, b), (u, v))
    right = NaturalFaceSelection((0, 2), (0, 2), (a, c), (u, w))
    dominated = NaturalFaceSelection((0,), (0,), (a,), (u,))
    result = maximal_face_selections((dominated, right, left))
    assert {value.selected_orbit_indices for value in result} == {(0, 1), (0, 2)}


def test_search_is_deterministic_and_source_replay_rejects_tampering():
    fixture = _reduced_symmetry_fixture()
    first = _search(fixture)
    second = _search(fixture)
    assert first == second
    restored = NaturalTilingSearchResult.from_dict(
        first.to_dict(),
        view=fixture.view,
        discovery=fixture.discovery,
        embedding=fixture.embedding,
        ring_index=fixture.ring_index,
        strength_catalog=_strength_catalog(fixture),
        face_certificates=fixture.face_certificates,
        master_witnesses=fixture.witnesses,
        compatibility=_compatibility(fixture),
        master_complex=fixture.complex,
        master_partition=fixture.partition,
    )
    assert restored == first
    payload = deepcopy(first.to_dict())
    payload["attempted_selection_count"] += 1
    with pytest.raises(NaturalTilingSearchSerializationError, match="not canonical"):
        NaturalTilingSearchResult.from_dict(
            payload,
            view=fixture.view,
            discovery=fixture.discovery,
            embedding=fixture.embedding,
            ring_index=fixture.ring_index,
            strength_catalog=_strength_catalog(fixture),
            face_certificates=fixture.face_certificates,
            master_witnesses=fixture.witnesses,
            compatibility=_compatibility(fixture),
            master_complex=fixture.complex,
            master_partition=fixture.partition,
        )
