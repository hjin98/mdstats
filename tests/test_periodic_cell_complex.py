from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from itertools import permutations
from types import SimpleNamespace

import pytest

from mdstats.analysis import (
    AuxiliaryVertexOrbit,
    AuxiliaryVertexRef,
    FaceCompatibilityConstraint,
    FaceCompatibilityConstraintSystem,
    FaceConstraintKind,
    FaceEmbeddingWitness,
    FacePlacementCertificate,
    FacePlacementStatus,
    FaceWitnessAssignment,
    FaceWitnessMethod,
    NetViewPolicy,
    PeriodicCellComplex,
    PeriodicCellComplexInvariantError,
    PeriodicCellComplexResourceError,
    PeriodicCellComplexSerializationError,
    PeriodicNetComponent,
    PeriodicNetEmbedding,
    PeriodicNetEmbeddingMethod,
    PeriodicNetView,
    PeriodicPartitionCertificate,
    PeriodicPartitionResources,
    PeriodicTetrahedron,
    PeriodicTileShell,
    ProjectedEdgeCurveModel,
    RingPlacement,
    TetrahedronPairRelation,
    TilePlacementRef,
    TranslatedCellTerm,
    build_periodic_cell_complex,
    certify_periodic_tetrahedral_partition,
    classify_tetrahedron_pair,
    make_face_placement,
)
from mdstats.analysis.framework_topology import FrameworkEdgeKey
from mdstats.analysis.primitive_ring import (
    LiftedVertexRef,
    PrimitiveRing,
    PrimitiveRingCatalog,
    PrimitiveRingEdgeSearch,
    PrimitiveRingEdgeToken,
    PrimitiveRingFamily,
    PrimitiveRingKey,
    PrimitiveRingOptions,
    PrimitiveRingSearchDiagnostics,
    PrimitiveRingSearchMethod,
    PrimitiveRingSearchStatus,
    PrimitiveRingSizeCount,
    PrimitiveRingStep,
    canonicalize_primitive_ring_tokens,
)
from mdstats.analysis.primitive_ring_index import build_primitive_ring_index

F = Fraction
ZERO = (0, 0, 0)


def _canonical_steps(
    raw_steps: tuple[tuple[int, int], ...],
    edges: tuple[FrameworkEdgeKey, ...],
) -> tuple[tuple[PrimitiveRingStep, ...], PrimitiveRingKey]:
    steps = tuple(PrimitiveRingStep(index, orientation) for index, orientation in raw_steps)
    tokens = tuple(PrimitiveRingEdgeToken(edges[step.edge_index], step.orientation) for step in steps)
    canonical = canonicalize_primitive_ring_tokens(tokens)
    candidates = []
    for rotation in range(len(steps)):
        candidate = steps[rotation:] + steps[:rotation]
        candidates.append(candidate)
    reversed_steps = tuple(step.reversed() for step in reversed(steps))
    for rotation in range(len(steps)):
        candidate = reversed_steps[rotation:] + reversed_steps[:rotation]
        candidates.append(candidate)
    for candidate in candidates:
        candidate_tokens = tuple(
            PrimitiveRingEdgeToken(edges[step.edge_index], step.orientation)
            for step in candidate
        )
        if candidate_tokens == canonical:
            return candidate, PrimitiveRingKey(canonical)
    raise AssertionError("Fixture ring could not be canonicalized.")


def _simple_cubic_fixture(*, witness_triangles=((0, 1, 2), (0, 2, 3))):
    edges = tuple(
        sorted(
            (
                FrameworkEdgeKey(0, 0, (1, 0, 0), (), (), "x"),
                FrameworkEdgeKey(0, 0, (0, 1, 0), (), (), "y"),
                FrameworkEdgeKey(0, 0, (0, 0, 1), (), (), "z"),
            )
        )
    )
    edge_index = {edge.rule_id: index for index, edge in enumerate(edges)}
    raw_rings = (
        ((edge_index["x"], 1), (edge_index["y"], 1), (edge_index["x"], -1), (edge_index["y"], -1)),
        ((edge_index["x"], 1), (edge_index["z"], 1), (edge_index["x"], -1), (edge_index["z"], -1)),
        ((edge_index["y"], 1), (edge_index["z"], 1), (edge_index["y"], -1), (edge_index["z"], -1)),
    )
    records = []
    for raw_steps in raw_rings:
        steps, key = _canonical_steps(raw_steps, edges)
        shift = ZERO
        vertices = []
        for step in steps:
            vertices.append(LiftedVertexRef(0, shift))
            delta = edges[step.edge_index].image_shift
            shift = tuple(shift[axis] + step.orientation * delta[axis] for axis in range(3))
        assert shift == ZERO
        records.append((key, steps, tuple(vertices)))
    records.sort(key=lambda value: value[0])
    rings = tuple(
        PrimitiveRing(
            ring_id,
            4,
            steps,
            vertices,
            ZERO,
            key,
            generator_kinds=("simple-cubic-fixture",),
        )
        for ring_id, (key, steps, vertices) in enumerate(records)
    )
    edge_searches = tuple(
        PrimitiveRingEdgeSearch(
            index,
            edge,
            PrimitiveRingSearchStatus.NOT_APPLICABLE,
            None,
            None,
            True,
            0,
            0,
            0,
            0,
            0,
            4,
        )
        for index, edge in enumerate(edges)
    )
    edge_to_ring_ids = tuple(
        tuple(ring.ring_id for ring in rings if any(step.edge_index == edge_id for step in ring.steps))
        for edge_id in range(len(edges))
    )
    catalog = PrimitiveRingCatalog(
        topology_digest="1" * 64,
        topology_graph_digest="2" * 64,
        options=PrimitiveRingOptions(max_ring_size=4),
        search_method=PrimitiveRingSearchMethod.SHORTEST_PATH_PAIRS,
        ring_family=PrimitiveRingFamily.PRIMITIVE_NO_SHORTCUT,
        rings=rings,
        edge_searches=edge_searches,
        ring_size_counts=(PrimitiveRingSizeCount(4, 3),),
        vertex_atom_indices=(0,),
        vertex_to_ring_ids=((0, 1, 2),),
        edge_to_ring_ids=edge_to_ring_ids,
        diagnostics=PrimitiveRingSearchDiagnostics(index_depth=2),
        search_completed_without_resource_truncation=True,
        complete_for_ring_sizes_up_to=4,
    )
    ring_index = build_primitive_ring_index(catalog)
    view = PeriodicNetView(
        source_graph_digest="2" * 64,
        source_topology_digest="1" * 64,
        pbc=(True, True, True),
        policy=NetViewPolicy.unlabeled_framework_net(),
        vertex_atom_indices=(0,),
        edge_keys=edges,
        vertex_signatures=(("framework_vertex",),),
        edge_signatures=(("framework_edge",),) * 3,
        components=(PeriodicNetComponent(0, (0,), (0, 1, 2), ((0, 0, 1), (0, 1, 0), (1, 0, 0)), 3, 1),),
    )
    embedding = PeriodicNetEmbedding(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        periodic_net_symmetry_digest="3" * 64,
        barycentric_placement_digest="4" * 64,
        symmetry_discovery_certificate_digest="5" * 64,
        method=PeriodicNetEmbeddingMethod.BARYCENTRIC_EDGE_COVARIANCE,
        edge_curve_model=ProjectedEdgeCurveModel.STRAIGHT_SEGMENT,
        anchor_atom_index=0,
        vertex_atom_indices=(0,),
        edge_keys=edges,
        fractional_coordinates=((F(0), F(0), F(0)),),
        primitive_gram_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        metric_determinant=1,
        minimum_edge_length_squared=1,
        maximum_edge_length_squared=1,
    )
    face_certificates = []
    witnesses = []
    for ring in rings:
        face = make_face_placement(
            embedding,
            ring_index,
            RingPlacement(ring_index.topology_graph_digest, ring.key, ZERO),
        )
        witness = FaceEmbeddingWitness(
            face,
            0,
            FaceWitnessMethod.BOUNDARY_VERTEX_TRIANGULATION,
            tuple(witness_triangles),
            "a" * 64,
            "b" * 64,
            (),
        )
        certificate = FacePlacementCertificate(
            view.digest,
            view.source_graph_digest,
            embedding.digest,
            ring_index.catalog_digest,
            "c" * 64,
            face,
            1,
            (witness,),
            (),
            FacePlacementStatus.CERTIFIED_ADMISSIBLE,
        )
        face_certificates.append(certificate)
        witnesses.append(witness)

    face_ids = (0, 0, 1, 1, 2, 2)
    face_shifts = ((0, 1, 1), (1, 1, 1), (1, 0, 1), (1, 1, 1), (1, 1, 0), (1, 1, 1))
    face_signs = (1, -1, -1, 1, 1, -1)
    shell = PeriodicTileShell(
        0,
        tuple(
            TranslatedCellTerm(face_id, shift, sign)
            for face_id, shift, sign in zip(face_ids, face_shifts, face_signs, strict=True)
        ),
        "primitive cube",
    )
    complex_ = build_periodic_cell_complex(
        view,
        embedding,
        ring_index,
        face_certificates,
        witnesses,
        (shell,),
    )

    vertices = (AuxiliaryVertexOrbit(0, (F(0), F(0), F(0))),)
    tetrahedra = []
    for tetrahedron_index, axis_order in enumerate(permutations(range(3))):
        corner = [0, 0, 0]
        refs = [AuxiliaryVertexRef(0, tuple(corner))]
        for axis in axis_order:
            corner[axis] = 1
            refs.append(AuxiliaryVertexRef(0, tuple(corner)))
        tetrahedra.append(
            PeriodicTetrahedron(
                tetrahedron_index,
                tuple(refs),
                TilePlacementRef(0, ZERO),
            )
        )
    return SimpleNamespace(
        view=view,
        embedding=embedding,
        ring_index=ring_index,
        face_certificates=tuple(face_certificates),
        witnesses=tuple(witnesses),
        shell=shell,
        complex=complex_,
        auxiliary_vertices=vertices,
        tetrahedra=tuple(tetrahedra),
    )


def _unit_tetrahedron():
    return (
        (F(0), F(0), F(0)),
        (F(1), F(0), F(0)),
        (F(0), F(1), F(0)),
        (F(0), F(0), F(1)),
    )


def _translated(tetrahedron, shift):
    return tuple(
        tuple(point[axis] + shift[axis] for axis in range(3))
        for point in tetrahedron
    )


def test_exact_tetrahedron_pair_relations_distinguish_allowed_and_forbidden_cases():
    tetrahedron = _unit_tetrahedron()
    contained = (
        (F(1, 10), F(1, 10), F(1, 10)),
        (F(2, 10), F(1, 10), F(1, 10)),
        (F(1, 10), F(2, 10), F(1, 10)),
        (F(1, 10), F(1, 10), F(2, 10)),
    )
    assert classify_tetrahedron_pair(tetrahedron, _translated(tetrahedron, (2, 0, 0))) is TetrahedronPairRelation.DISJOINT
    assert classify_tetrahedron_pair(tetrahedron, _translated(tetrahedron, (1, 0, 0))) is TetrahedronPairRelation.BOUNDARY_CONTACT
    assert classify_tetrahedron_pair(tetrahedron, tetrahedron) is TetrahedronPairRelation.COINCIDENT_INTERIOR
    assert classify_tetrahedron_pair(tetrahedron, contained) is TetrahedronPairRelation.CONTAINMENT_OVERLAP
    assert classify_tetrahedron_pair(tetrahedron, _translated(tetrahedron, (F(1, 4), F(1, 4), F(1, 4)))) is TetrahedronPairRelation.IMPROPER_INTERIOR_OVERLAP


def test_simple_cubic_complex_has_translation_labelled_chain_algebra_and_spherical_shell():
    fixture = _simple_cubic_fixture()
    complex_ = fixture.complex
    assert complex_.cell_counts == (1, 3, 3, 1)
    assert complex_.cell_counts[0] - complex_.cell_counts[1] + complex_.cell_counts[2] - complex_.cell_counts[3] == 0
    assert complex_.tile_shell_invariants[0].genus_zero
    assert complex_.tile_shell_invariants[0].euler_characteristic == 2
    assert all(len(column) == 2 for column in complex_.boundary_1.columns)
    assert any(term.image_shift != ZERO for column in complex_.boundary_3.columns for term in column)
    assert fixture.complex == _simple_cubic_fixture().complex


def test_cell_complex_rejects_nonclosed_tile_shell():
    fixture = _simple_cubic_fixture()
    terms = list(fixture.shell.face_incidences)
    first = terms[0]
    terms[0] = TranslatedCellTerm(first.cell_index, first.image_shift, -first.coefficient)
    with pytest.raises(PeriodicCellComplexInvariantError, match=r"boundary_2 \* boundary_3"):
        build_periodic_cell_complex(
            fixture.view,
            fixture.embedding,
            fixture.ring_index,
            fixture.face_certificates,
            fixture.witnesses,
            (PeriodicTileShell(0, tuple(terms)),),
        )


def test_cell_complex_rejects_selected_unresolved_face_assignment():
    fixture = _simple_cubic_fixture()
    assignments = tuple(
        FaceWitnessAssignment(witness.face_placement.digest, witness.witness_id, witness.digest)
        for witness in fixture.witnesses
    )
    compatibility = FaceCompatibilityConstraintSystem(
        tuple(certificate.digest for certificate in fixture.face_certificates),
        assignments,
        (),
        (FaceCompatibilityConstraint(FaceConstraintKind.UNRESOLVED, (assignments[0],), "fixture unresolved"),),
    )
    with pytest.raises(PeriodicCellComplexInvariantError, match="unresolved compatibility"):
        build_periodic_cell_complex(
            fixture.view,
            fixture.embedding,
            fixture.ring_index,
            fixture.face_certificates,
            fixture.witnesses,
            (fixture.shell,),
            compatibility=compatibility,
        )


def test_periodic_cube_partition_is_certified_exactly():
    fixture = _simple_cubic_fixture()
    certificate = certify_periodic_tetrahedral_partition(
        fixture.complex,
        fixture.embedding,
        fixture.ring_index,
        fixture.witnesses,
        fixture.auxiliary_vertices,
        fixture.tetrahedra,
    )
    assert certificate.total_fractional_volume == 1
    assert certificate.tile_fractional_volumes == (F(1),)
    assert len(certificate.tetrahedra) == 6
    assert len(certificate.facet_pairs) == 12
    assert len(certificate.face_triangle_coverage) == 6
    assert {(value.face_index, value.triangle_index) for value in certificate.face_triangle_coverage} == {
        (face_index, triangle_index) for face_index in range(3) for triangle_index in range(2)
    }
    assert certificate.exact_tetrahedron_test_count > 0


def test_partition_rejects_coincident_tetrahedron_interior():
    fixture = _simple_cubic_fixture()
    duplicate = PeriodicTetrahedron(6, fixture.tetrahedra[0].vertices, TilePlacementRef(0, ZERO))
    with pytest.raises(PeriodicCellComplexInvariantError, match="invalid periodic interior relation"):
        certify_periodic_tetrahedral_partition(
            fixture.complex,
            fixture.embedding,
            fixture.ring_index,
            fixture.witnesses,
            fixture.auxiliary_vertices,
            fixture.tetrahedra + (duplicate,),
        )


def test_partition_rejects_nonconforming_face_triangulation():
    fixture = _simple_cubic_fixture(witness_triangles=((0, 1, 3), (1, 2, 3)))
    with pytest.raises(PeriodicCellComplexInvariantError, match="must match exactly one"):
        certify_periodic_tetrahedral_partition(
            fixture.complex,
            fixture.embedding,
            fixture.ring_index,
            fixture.witnesses,
            fixture.auxiliary_vertices,
            fixture.tetrahedra,
        )


def test_partition_rejects_incomplete_periodic_facet_pairing():
    fixture = _simple_cubic_fixture()
    with pytest.raises(PeriodicCellComplexInvariantError, match="exactly two tetrahedral incidences"):
        certify_periodic_tetrahedral_partition(
            fixture.complex,
            fixture.embedding,
            fixture.ring_index,
            fixture.witnesses,
            fixture.auxiliary_vertices,
            fixture.tetrahedra[:-1],
        )


def test_partition_resource_guard_is_transactional():
    fixture = _simple_cubic_fixture()
    with pytest.raises(PeriodicCellComplexResourceError, match="size exceeds"):
        certify_periodic_tetrahedral_partition(
            fixture.complex,
            fixture.embedding,
            fixture.ring_index,
            fixture.witnesses,
            fixture.auxiliary_vertices,
            fixture.tetrahedra,
            resources=PeriodicPartitionResources(max_tetrahedra=5),
        )


def test_cell_complex_source_replay_accepts_canonical_payload_and_rejects_tampering():
    fixture = _simple_cubic_fixture()
    payload = fixture.complex.to_dict()
    rebuilt = PeriodicCellComplex.from_dict(
        payload,
        view=fixture.view,
        embedding=fixture.embedding,
        ring_index=fixture.ring_index,
        face_certificates=fixture.face_certificates,
        selected_witnesses=fixture.witnesses,
    )
    assert rebuilt == fixture.complex
    altered = deepcopy(payload)
    altered["tile_shells"][0]["label"] = "altered"
    with pytest.raises(PeriodicCellComplexSerializationError, match="not canonical"):
        PeriodicCellComplex.from_dict(
            altered,
            view=fixture.view,
            embedding=fixture.embedding,
            ring_index=fixture.ring_index,
            face_certificates=fixture.face_certificates,
            selected_witnesses=fixture.witnesses,
        )


def test_partition_source_replay_accepts_canonical_payload_and_rejects_tampering():
    fixture = _simple_cubic_fixture()
    certificate = certify_periodic_tetrahedral_partition(
        fixture.complex,
        fixture.embedding,
        fixture.ring_index,
        fixture.witnesses,
        fixture.auxiliary_vertices,
        fixture.tetrahedra,
    )
    payload = certificate.to_dict()
    rebuilt = PeriodicPartitionCertificate.from_dict(
        payload,
        complex_=fixture.complex,
        embedding=fixture.embedding,
        ring_index=fixture.ring_index,
        selected_witnesses=fixture.witnesses,
    )
    assert rebuilt == certificate
    altered = deepcopy(payload)
    altered["exact_tetrahedron_test_count"] += 1
    with pytest.raises(PeriodicCellComplexSerializationError, match="not canonical"):
        PeriodicPartitionCertificate.from_dict(
            altered,
            complex_=fixture.complex,
            embedding=fixture.embedding,
            ring_index=fixture.ring_index,
            selected_witnesses=fixture.witnesses,
        )
