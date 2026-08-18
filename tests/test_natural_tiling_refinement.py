from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from mdstats.analysis import (
    NaturalTilingRefinementInputError,
    NaturalTilingRefinementResourceError,
    NaturalTilingRefinementResources,
    NaturalTilingRefinementSerializationError,
    PrimitiveBoundBuild,
    PrimitiveBoundRefinementReport,
    RefinementChangeKind,
    RefinementRecordCategory,
    RefinementSnapshotStatus,
    RefinementTransitionStatus,
    build_primitive_bound_refinement_report,
    build_primitive_bound_snapshot,
    build_primitive_ring_index,
    certify_periodic_tetrahedral_partition,
    discover_periodic_net_symmetry,
    run_primitive_bound_refinement,
    search_natural_tilings_from_master_refinement,
)
from mdstats.analysis.face_candidates import (
    FaceEmbeddingWitness,
    FacePlacementCertificate,
    FaceWitnessMethod,
    FacePlacementStatus,
    make_face_placement,
)
from mdstats.analysis.periodic_cycle import RingPlacement
from tests.test_natural_tiling import _compatibility, _strength_catalog
from tests.test_periodic_cell_complex import _simple_cubic_fixture

ZERO = (0, 0, 0)


def _bound_build(bound: int, *, unresolved: bool = False) -> PrimitiveBoundBuild:
    source = _simple_cubic_fixture()
    catalog = replace(
        source.ring_index.catalog,
        options=replace(source.ring_index.catalog.options, max_ring_size=bound),
        complete_for_ring_sizes_up_to=bound,
        digest="",
    )
    ring_index = build_primitive_ring_index(catalog)

    certificates = []
    witnesses = []
    for old_certificate, old_witness in zip(
        source.face_certificates, source.witnesses, strict=True
    ):
        face = make_face_placement(
            source.embedding,
            ring_index,
            RingPlacement(
                ring_index.topology_graph_digest,
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
            source.view.digest,
            source.view.source_graph_digest,
            source.embedding.digest,
            ring_index.catalog_digest,
            old_certificate.periodic_edge_intersection_certificate_digest,
            face,
            1,
            (witness,),
            (),
            FacePlacementStatus.CERTIFIED_ADMISSIBLE,
        )
        certificates.append(certificate)
        witnesses.append(witness)

    fixture = SimpleNamespace(
        view=source.view,
        embedding=source.embedding,
        ring_index=ring_index,
        face_certificates=tuple(certificates),
        witnesses=tuple(witnesses),
        shell=source.shell,
        auxiliary_vertices=source.auxiliary_vertices,
        tetrahedra=source.tetrahedra,
    )
    from mdstats.analysis import build_periodic_cell_complex

    fixture.complex = build_periodic_cell_complex(
        fixture.view,
        fixture.embedding,
        fixture.ring_index,
        fixture.face_certificates,
        fixture.witnesses,
        (fixture.shell,),
    )
    fixture.partition = certify_periodic_tetrahedral_partition(
        fixture.complex,
        fixture.embedding,
        fixture.ring_index,
        fixture.witnesses,
        fixture.auxiliary_vertices,
        fixture.tetrahedra,
    )
    fixture.discovery = discover_periodic_net_symmetry(
        fixture.view, ring_index=fixture.ring_index
    )
    fixture.strength = _strength_catalog(fixture)
    fixture.compatibility = _compatibility(fixture)
    fixture.search = search_natural_tilings_from_master_refinement(
        fixture.view,
        fixture.discovery,
        fixture.embedding,
        fixture.ring_index,
        fixture.strength,
        fixture.face_certificates,
        fixture.witnesses,
        fixture.compatibility,
        fixture.complex,
        fixture.partition,
    )
    return PrimitiveBoundBuild(
        bound,
        fixture.view.digest,
        fixture.embedding.digest,
        fixture.ring_index,
        fixture.discovery.ring_symmetry,
        fixture.strength,
        fixture.face_certificates,
        (fixture.compatibility,),
        (fixture.complex,),
        (fixture.partition,),
        (fixture.search,),
        unresolved_reasons=("fixture unresolved",) if unresolved else (),
    )


def test_complete_rebuilds_ignore_dense_catalog_digests_and_stabilize_by_scientific_keys():
    lower = build_primitive_bound_snapshot(_bound_build(4))
    upper = build_primitive_bound_snapshot(_bound_build(6))
    assert lower.primitive_ring_catalog_digest != upper.primitive_ring_catalog_digest
    report = build_primitive_bound_refinement_report((lower, upper))
    assert report.status is RefinementTransitionStatus.STABLE
    assert report.stable_tested_suffix_start == 4
    assert report.transitions[0].changes == ()
    assert lower.outcome == upper.outcome


def test_runner_invokes_one_independent_rebuild_per_strictly_increasing_bound():
    calls = []

    def rebuild(bound):
        calls.append(bound)
        return _bound_build(bound)

    report = run_primitive_bound_refinement((4, 6, 8), rebuild)
    assert calls == [4, 6, 8]
    assert report.status is RefinementTransitionStatus.STABLE
    assert report.stable_tested_suffix_start == 4


def test_bound_mismatch_rejects_reused_source_bound_objects():
    build = _bound_build(4)
    with pytest.raises(NaturalTilingRefinementInputError, match="options bound"):
        replace(build, primitive_ring_bound=6)


def test_removed_complete_ring_key_is_an_invalid_monotonicity_violation():
    lower = build_primitive_bound_snapshot(_bound_build(4))
    upper = build_primitive_bound_snapshot(_bound_build(6))
    ring_records = [
        value for value in upper.records
        if value.category is RefinementRecordCategory.RING
    ]
    altered = replace(
        upper,
        records=tuple(
            value for value in upper.records
            if value is not ring_records[0]
        ),
        digest="",
    )
    transition = build_primitive_bound_refinement_report((lower, altered)).transitions[0]
    assert transition.status is RefinementTransitionStatus.INVALID
    assert transition.monotonicity_violations
    assert any(
        value.category is RefinementRecordCategory.RING
        and value.kind is RefinementChangeKind.REMOVED
        for value in transition.changes
    )


def test_changed_strength_state_is_reported_without_losing_ring_identity():
    lower = build_primitive_bound_snapshot(_bound_build(4))
    upper = build_primitive_bound_snapshot(_bound_build(6))
    index = next(
        i for i, value in enumerate(upper.records)
        if value.category is RefinementRecordCategory.STRENGTH
    )
    old = upper.records[index]
    changed = replace(old, state_json='{"fixture":"changed"}', key_digest="", state_digest="")
    records = list(upper.records)
    records[index] = changed
    altered = replace(upper, records=tuple(records), digest="")
    transition = build_primitive_bound_refinement_report((lower, altered)).transitions[0]
    assert transition.status is RefinementTransitionStatus.CHANGED
    assert any(
        value.category is RefinementRecordCategory.STRENGTH
        and value.kind is RefinementChangeKind.MODIFIED
        for value in transition.changes
    )


def test_unresolved_snapshot_makes_transition_conditional_even_when_keys_are_stable():
    lower = build_primitive_bound_snapshot(_bound_build(4))
    upper = build_primitive_bound_snapshot(_bound_build(6, unresolved=True))
    assert upper.status is RefinementSnapshotStatus.UNRESOLVED
    report = build_primitive_bound_refinement_report((lower, upper))
    assert report.status is RefinementTransitionStatus.UNRESOLVED
    assert report.transitions[0].status is RefinementTransitionStatus.UNRESOLVED
    assert report.stable_tested_suffix_start is None


def test_resource_preflight_rejects_bound_family_before_callback_execution():
    calls = []
    with pytest.raises(NaturalTilingRefinementResourceError, match="max_bounds"):
        run_primitive_bound_refinement(
            (4, 6),
            lambda bound: calls.append(bound),
            resources=NaturalTilingRefinementResources(max_bounds=1),
        )
    assert calls == []


def test_bounds_must_be_unique_and_strictly_increasing():
    with pytest.raises(NaturalTilingRefinementInputError, match="strictly increasing"):
        run_primitive_bound_refinement((6, 4), _bound_build)
    with pytest.raises(NaturalTilingRefinementInputError, match="strictly increasing"):
        run_primitive_bound_refinement((4, 4), _bound_build)


def test_report_serialization_round_trip_recomputes_every_transition():
    report = run_primitive_bound_refinement((4, 6), _bound_build)
    rebuilt = PrimitiveBoundRefinementReport.from_dict(report.to_dict())
    assert rebuilt == report


def test_report_serialization_rejects_tampered_transition():
    report = run_primitive_bound_refinement((4, 6), _bound_build)
    payload = deepcopy(report.to_dict())
    payload["transitions"][0]["status"] = RefinementTransitionStatus.CHANGED.value
    with pytest.raises(
        (NaturalTilingRefinementInputError, NaturalTilingRefinementSerializationError)
    ):
        PrimitiveBoundRefinementReport.from_dict(payload)
