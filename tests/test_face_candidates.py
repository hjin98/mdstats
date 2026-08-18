from __future__ import annotations

from fractions import Fraction
import json

import numpy as np
import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    ExplicitConnectivity,
    FaceCandidateResourceError,
    FaceCandidateSerializationError,
    FaceConstraintKind,
    FaceEmbeddingResources,
    FacePlacementStatus,
    FaceWitnessAssignment,
    FaceWitnessPairStatus,
    FrameworkAtomRole,
    FrameworkEdgeKey,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    NetViewPolicy,
    PeriodicNetComponent,
    PeriodicNetEmbedding,
    PeriodicNetEmbeddingMethod,
    PeriodicNetView,
    PrimitiveRingOptions,
    ProjectedEdgeCurveModel,
    RingPlacement,
    build_atomic_connectivity_state,
    build_face_compatibility_constraint_system,
    build_face_placement_certificate,
    build_framework_topology,
    build_primitive_ring_index,
    certify_face_witness_pair,
    certify_periodic_straight_edge_embedding,
    enumerate_primitive_rings,
    make_face_placement,
)
from mdstats.analysis._robust_geometry import (
    IntersectionDimension,
    segment_triangle_intersection,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics


F = Fraction
ZERO = (0, 0, 0)


def _collection(n_atoms: int) -> AtomisticFrameCollection:
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=np.full(n_atoms, 14, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.asarray((True, True, True), dtype=bool),
        steps=None,
        times=None,
        cells=np.eye(3)[None, ...],
        origins=np.zeros((1, 3)),
        fractional_positions=np.zeros((1, n_atoms, 3)),
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _direct_topology(
    n_vertices: int,
    edge_pairs: tuple[tuple[int, int], ...],
) -> FrameworkTopology:
    state = build_atomic_connectivity_state(
        _collection(n_vertices),
        ExplicitConnectivity(
            uniform_edges=tuple(AtomicEdgeKey(i, j) for i, j in edge_pairs)
        ),
        frame_index=0,
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": FrameworkAtomRole.VERTEX},
        path_rules=(FrameworkPathRule("direct", (), edge_kind="direct"),),
        name="direct graph",
    )
    return build_framework_topology(state, mapping)


def _sources(
    coordinates: tuple[tuple[Fraction, Fraction, Fraction], ...],
    edge_pairs: tuple[tuple[int, int], ...],
    *,
    max_ring_size: int = 8,
):
    origin = coordinates[0]
    coordinates = tuple(
        tuple(point[axis] - origin[axis] for axis in range(3))
        for point in coordinates
    )
    topology = _direct_topology(len(coordinates), edge_pairs)
    catalog = enumerate_primitive_rings(
        topology, options=PrimitiveRingOptions(max_ring_size=max_ring_size)
    )
    ring_index = build_primitive_ring_index(catalog)

    edge_keys = tuple(sorted(topology.edge_keys))
    component = PeriodicNetComponent(
        component_id=0,
        vertex_positions=tuple(range(len(coordinates))),
        edge_positions=tuple(range(len(edge_keys))),
        cycle_gain_generators=((0, 0, 1), (0, 1, 0), (1, 0, 0)),
        translation_rank=3,
        translation_index=1,
    )
    view = PeriodicNetView(
        source_graph_digest=topology.graph_digest,
        source_topology_digest=topology.digest,
        pbc=(True, True, True),
        policy=NetViewPolicy.unlabeled_framework_net(),
        vertex_atom_indices=tuple(range(len(coordinates))),
        edge_keys=edge_keys,
        vertex_signatures=(("framework_vertex",),) * len(coordinates),
        edge_signatures=(("framework_edge",),) * len(edge_keys),
        components=(component,),
    )
    squared = []
    for edge in edge_keys:
        start = coordinates[edge.vertex_i]
        end = tuple(
            coordinates[edge.vertex_j][axis] + edge.image_shift[axis]
            for axis in range(3)
        )
        delta = tuple(end[axis] - start[axis] for axis in range(3))
        squared.append(sum(value * value for value in delta))
    embedding = PeriodicNetEmbedding(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        periodic_net_symmetry_digest="3" * 64,
        barycentric_placement_digest="4" * 64,
        symmetry_discovery_certificate_digest="5" * 64,
        method=PeriodicNetEmbeddingMethod.BARYCENTRIC_EDGE_COVARIANCE,
        edge_curve_model=ProjectedEdgeCurveModel.STRAIGHT_SEGMENT,
        anchor_atom_index=0,
        vertex_atom_indices=view.vertex_atom_indices,
        edge_keys=view.edge_keys,
        fractional_coordinates=coordinates,
        primitive_gram_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        metric_determinant=1,
        minimum_edge_length_squared=min(squared),
        maximum_edge_length_squared=max(squared),
    )
    edge_certificate = certify_periodic_straight_edge_embedding(view, embedding)
    return view, embedding, ring_index, edge_certificate


def _face_certificate(view, embedding, ring_index, edge_certificate, ring_id: int):
    ring = ring_index.ring_for_key(ring_index.ring_keys[ring_id])
    placement = RingPlacement(ring_index.topology_graph_digest, ring.key, ZERO)
    face = make_face_placement(embedding, ring_index, placement)
    return build_face_placement_certificate(
        view, embedding, ring_index, edge_certificate, face
    )


def test_planar_square_has_mesh_independent_face_and_two_admissible_witnesses() -> None:
    coordinates = (
        (F(1, 4), F(1, 4), F(1, 2)),
        (F(3, 4), F(1, 4), F(1, 2)),
        (F(3, 4), F(3, 4), F(1, 2)),
        (F(1, 4), F(3, 4), F(1, 2)),
    )
    sources = _sources(coordinates, ((0, 1), (1, 2), (2, 3), (0, 3)))
    certificate = _face_certificate(*sources, 0)

    assert certificate.status is FacePlacementStatus.CERTIFIED_ADMISSIBLE
    assert certificate.triangulation_candidate_count == 2
    assert len(certificate.witnesses) == 2
    assert all(witness.face_placement == certificate.face_placement for witness in certificate.witnesses)
    assert len({witness.triangles for witness in certificate.witnesses}) == 2
    assert all(witness.admissible for witness in certificate.witnesses)


def test_nonplanar_quadrilateral_retains_at_least_one_embedded_disk() -> None:
    coordinates = (
        (F(1, 4), F(1, 4), F(2, 5)),
        (F(3, 4), F(1, 4), F(3, 5)),
        (F(3, 4), F(3, 4), F(2, 5)),
        (F(1, 4), F(3, 4), F(3, 5)),
    )
    sources = _sources(coordinates, ((0, 1), (1, 2), (2, 3), (0, 3)))
    certificate = _face_certificate(*sources, 0)

    assert certificate.status is FacePlacementStatus.CERTIFIED_ADMISSIBLE
    assert certificate.witnesses


def test_framework_penetration_is_not_confused_with_disk_nonembeddedness() -> None:
    coordinates = (
        (F(1, 4), F(1, 4), F(1, 2)),
        (F(3, 4), F(1, 4), F(1, 2)),
        (F(3, 4), F(3, 4), F(1, 2)),
        (F(1, 4), F(3, 4), F(1, 2)),
        (F(1, 2), F(1, 2), F(1, 4)),
        (F(1, 2), F(1, 2), F(3, 4)),
    )
    edges = ((0, 1), (1, 2), (2, 3), (0, 3), (4, 5))
    sources = _sources(coordinates, edges)
    certificate = _face_certificate(*sources, 0)

    assert certificate.status is FacePlacementStatus.UNRESOLVED_NO_ADMISSIBLE_WITNESS
    assert certificate.witnesses
    assert all(witness.framework_contacts for witness in certificate.witnesses)
    assert not certificate.rejections


def test_hopf_link_has_nonzero_algebraic_intersection_certificate() -> None:
    coordinates = (
        (F(1, 4), F(1, 4), F(1, 2)),
        (F(3, 4), F(1, 4), F(1, 2)),
        (F(3, 4), F(3, 4), F(1, 2)),
        (F(1, 4), F(3, 4), F(1, 2)),
        (F(1, 2), F(1, 2), F(1, 4)),
        (F(1, 2), F(7, 8), F(1, 4)),
        (F(1, 2), F(7, 8), F(3, 4)),
        (F(1, 2), F(1, 2), F(3, 4)),
    )
    edges = (
        (0, 1), (1, 2), (2, 3), (0, 3),
        (4, 5), (5, 6), (6, 7), (4, 7),
    )
    view, embedding, ring_index, edge_certificate = _sources(coordinates, edges)
    certificates = [
        _face_certificate(view, embedding, ring_index, edge_certificate, ring_id)
        for ring_id in range(2)
    ]
    pair = certify_face_witness_pair(
        embedding, ring_index, certificates[0].witnesses[0], certificates[1].witnesses[0]
    )

    assert pair.status is FaceWitnessPairStatus.PROVEN_LINKED_NONZERO_INTERSECTION
    assert any(value.intersection_number != 0 for value in pair.algebraic_intersections)


def test_parallel_disjoint_squares_supply_an_unlinking_witness() -> None:
    coordinates = (
        (F(1, 5), F(1, 5), F(1, 4)),
        (F(2, 5), F(1, 5), F(1, 4)),
        (F(2, 5), F(2, 5), F(1, 4)),
        (F(1, 5), F(2, 5), F(1, 4)),
        (F(3, 5), F(3, 5), F(3, 4)),
        (F(4, 5), F(3, 5), F(3, 4)),
        (F(4, 5), F(4, 5), F(3, 4)),
        (F(3, 5), F(4, 5), F(3, 4)),
    )
    edges = (
        (0, 1), (1, 2), (2, 3), (0, 3),
        (4, 5), (5, 6), (6, 7), (4, 7),
    )
    view, embedding, ring_index, edge_certificate = _sources(coordinates, edges)
    left = _face_certificate(view, embedding, ring_index, edge_certificate, 0)
    right = _face_certificate(view, embedding, ring_index, edge_certificate, 1)
    pair = certify_face_witness_pair(
        embedding, ring_index, left.witnesses[0], right.witnesses[0]
    )

    assert pair.status is FaceWitnessPairStatus.DISJOINT_DISK_WITNESS
    assert all(value.intersection_number == 0 for value in pair.algebraic_intersections)



def test_intersecting_particular_disks_are_incompatible_not_proven_linked() -> None:
    coordinates = (
        (F(1, 5), F(1, 5), F(1, 2)),
        (F(4, 5), F(1, 5), F(1, 2)),
        (F(4, 5), F(4, 5), F(1, 2)),
        (F(1, 5), F(4, 5), F(1, 2)),
        (F(1, 2), F(2, 5), F(2, 5)),
        (F(1, 2), F(3, 5), F(2, 5)),
        (F(1, 2), F(3, 5), F(3, 5)),
        (F(1, 2), F(2, 5), F(3, 5)),
    )
    edges = (
        (0, 1), (1, 2), (2, 3), (0, 3),
        (4, 5), (5, 6), (6, 7), (4, 7),
    )
    view, embedding, ring_index, edge_certificate = _sources(coordinates, edges)
    left = _face_certificate(view, embedding, ring_index, edge_certificate, 0)
    right = _face_certificate(view, embedding, ring_index, edge_certificate, 1)
    pair = certify_face_witness_pair(
        embedding, ring_index, left.witnesses[0], right.witnesses[0]
    )

    assert pair.status is FaceWitnessPairStatus.WITNESS_PAIR_INCOMPATIBLE
    assert pair.incompatible_surface_contact_count > 0
    assert all(value.intersection_number == 0 for value in pair.algebraic_intersections)

def test_shared_boundary_faces_are_compatible_only_on_the_shared_feature() -> None:
    coordinates = (
        (F(1, 4), F(1, 2), F(1, 2)),
        (F(3, 4), F(1, 2), F(1, 2)),
        (F(1, 2), F(3, 4), F(1, 2)),
        (F(1, 2), F(1, 4), F(1, 2)),
    )
    edges = ((0, 1), (1, 2), (0, 2), (1, 3), (0, 3))
    view, embedding, ring_index, edge_certificate = _sources(coordinates, edges)
    assert len(ring_index.ring_keys) == 2
    left = _face_certificate(view, embedding, ring_index, edge_certificate, 0)
    right = _face_certificate(view, embedding, ring_index, edge_certificate, 1)
    pair = certify_face_witness_pair(
        embedding, ring_index, left.witnesses[0], right.witnesses[0]
    )

    assert pair.status is FaceWitnessPairStatus.COMPATIBLE_SHARED_BOUNDARY
    assert pair.allowed_shared_boundary_contact_count > 0


def test_constraint_system_preserves_caller_declared_higher_order_restriction() -> None:
    coordinates = (
        (F(1, 10), F(1, 10), F(1, 5)), (F(2, 10), F(1, 10), F(1, 5)),
        (F(2, 10), F(2, 10), F(1, 5)), (F(1, 10), F(2, 10), F(1, 5)),
        (F(4, 10), F(4, 10), F(1, 2)), (F(5, 10), F(4, 10), F(1, 2)),
        (F(5, 10), F(5, 10), F(1, 2)), (F(4, 10), F(5, 10), F(1, 2)),
        (F(7, 10), F(7, 10), F(4, 5)), (F(8, 10), F(7, 10), F(4, 5)),
        (F(8, 10), F(8, 10), F(4, 5)), (F(7, 10), F(8, 10), F(4, 5)),
    )
    edges = tuple(
        edge
        for offset in (0, 4, 8)
        for edge in ((offset, offset + 1), (offset + 1, offset + 2),
                     (offset + 2, offset + 3), (offset, offset + 3))
    )
    view, embedding, ring_index, edge_certificate = _sources(coordinates, edges)
    certificates = tuple(
        _face_certificate(view, embedding, ring_index, edge_certificate, index)
        for index in range(3)
    )
    assignments = tuple(
        FaceWitnessAssignment(
            certificate.face_placement.digest,
            certificate.witnesses[0].witness_id,
            certificate.witnesses[0].digest,
        )
        for certificate in certificates
    )
    system = build_face_compatibility_constraint_system(
        embedding,
        ring_index,
        certificates,
        higher_order_forbidden=(assignments,),
    )

    assert any(
        constraint.kind is FaceConstraintKind.HIGHER_ORDER_FORBIDDEN
        and constraint.assignments == tuple(sorted(assignments))
        for constraint in system.constraints
    )



def test_face_and_pair_certificates_replay_serialized_sources() -> None:
    coordinates = (
        (F(1, 5), F(1, 5), F(1, 4)),
        (F(2, 5), F(1, 5), F(1, 4)),
        (F(2, 5), F(2, 5), F(1, 4)),
        (F(1, 5), F(2, 5), F(1, 4)),
        (F(3, 5), F(3, 5), F(3, 4)),
        (F(4, 5), F(3, 5), F(3, 4)),
        (F(4, 5), F(4, 5), F(3, 4)),
        (F(3, 5), F(4, 5), F(3, 4)),
    )
    edges = (
        (0, 1), (1, 2), (2, 3), (0, 3),
        (4, 5), (5, 6), (6, 7), (4, 7),
    )
    view, embedding, ring_index, edge_certificate = _sources(coordinates, edges)
    left = _face_certificate(view, embedding, ring_index, edge_certificate, 0)
    right = _face_certificate(view, embedding, ring_index, edge_certificate, 1)
    restored_left = type(left).from_dict(
        json.loads(json.dumps(left.to_dict())),
        view=view,
        embedding=embedding,
        ring_index=ring_index,
        edge_certificate=edge_certificate,
    )
    pair = certify_face_witness_pair(
        embedding, ring_index, left.witnesses[0], right.witnesses[0]
    )
    restored_pair = type(pair).from_dict(
        json.loads(json.dumps(pair.to_dict())),
        embedding=embedding,
        ring_index=ring_index,
        left_witness=left.witnesses[0],
        right_witness=right.witnesses[0],
    )

    assert restored_left == left
    assert restored_pair == pair

    tampered = json.loads(json.dumps(left.to_dict()))
    tampered["status"] = FacePlacementStatus.UNRESOLVED_NO_EMBEDDED_WITNESS.value
    with pytest.raises(FaceCandidateSerializationError, match="not canonical"):
        type(left).from_dict(
            tampered,
            view=view,
            embedding=embedding,
            ring_index=ring_index,
            edge_certificate=edge_certificate,
        )

def test_boundary_triangulation_resource_limit_fails_transactionally() -> None:
    coordinates = (
        (F(1, 5), F(1, 5), F(1, 2)),
        (F(2, 5), F(1, 5), F(1, 2)),
        (F(3, 5), F(2, 5), F(1, 2)),
        (F(3, 5), F(3, 5), F(1, 2)),
        (F(2, 5), F(4, 5), F(1, 2)),
        (F(1, 5), F(3, 5), F(1, 2)),
    )
    edges = tuple((index, (index + 1) % 6) for index in range(6))
    view, embedding, ring_index, edge_certificate = _sources(coordinates, edges)
    ring = ring_index.ring_for_key(ring_index.ring_keys[0])
    face = make_face_placement(
        embedding,
        ring_index,
        RingPlacement(ring_index.topology_graph_digest, ring.key, ZERO),
    )
    with pytest.raises(FaceCandidateResourceError, match="exceeding"):
        build_face_placement_certificate(
            view,
            embedding,
            ring_index,
            edge_certificate,
            face,
            resources=FaceEmbeddingResources(max_triangulations=10),
        )


def test_exact_segment_triangle_predicate_resolves_tiny_transverse_offset() -> None:
    epsilon = F(1, 10**18)
    exact = segment_triangle_intersection(
        (F(1, 4), F(1, 4), -epsilon),
        (F(1, 4), F(1, 4), epsilon),
        ((F(0), F(0), F(0)), (F(1), F(0), F(0)), (F(0), F(1), F(0))),
    )

    assert exact.dimension is IntersectionDimension.POINT
    assert exact.transverse_sign in (-1, 1)
    assert exact.points == ((F(1, 4), F(1, 4), F(0)),)
