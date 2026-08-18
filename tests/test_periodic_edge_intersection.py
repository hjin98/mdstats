from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from mdstats.analysis import (
    FrameworkEdgeKey,
    FrameworkTopology,
    NetViewPolicy,
    PeriodicNetComponent,
    PeriodicNetEmbedding,
    PeriodicNetEmbeddingMethod,
    PeriodicNetView,
    PeriodicSpatialMethod,
    ProjectedEdgeCurveModel,
    build_periodic_net_embedding,
    build_periodic_net_view,
    discover_periodic_net_symmetry,
)
from mdstats.analysis.periodic_edge_intersection import (
    PeriodicEdgeContactKind,
    PeriodicEdgeIntersectionCertificate,
    PeriodicEdgeIntersectionSerializationError,
    PeriodicEdgeIntersectionStatus,
    certify_periodic_straight_edge_embedding,
)


def _manual_view_embedding(
    coordinates: tuple[tuple[Fraction, Fraction, Fraction], ...],
    edge_pairs: tuple[tuple[int, int, tuple[int, int, int], str], ...],
) -> tuple[PeriodicNetView, PeriodicNetEmbedding]:
    edge_keys = tuple(
        sorted(
            FrameworkEdgeKey(i, j, shift, (), (), rule)
            for i, j, shift, rule in edge_pairs
        )
    )
    component = PeriodicNetComponent(
        component_id=0,
        vertex_positions=tuple(range(len(coordinates))),
        edge_positions=tuple(range(len(edge_keys))),
        cycle_gain_generators=((0, 0, 1), (0, 1, 0), (1, 0, 0)),
        translation_rank=3,
        translation_index=1,
    )
    view = PeriodicNetView(
        source_graph_digest="1" * 64,
        source_topology_digest="2" * 64,
        pbc=(True, True, True),
        policy=NetViewPolicy.unlabeled_framework_net(),
        vertex_atom_indices=tuple(range(len(coordinates))),
        edge_keys=edge_keys,
        vertex_signatures=(('framework_vertex',),) * len(coordinates),
        edge_signatures=(('framework_edge',),) * len(edge_keys),
        components=(component,),
    )
    squared = []
    for edge in edge_keys:
        start = coordinates[edge.vertex_i]
        end = tuple(coordinates[edge.vertex_j][axis] + edge.image_shift[axis] for axis in range(3))
        displacement = tuple(end[axis] - start[axis] for axis in range(3))
        squared.append(sum(value * value for value in displacement))
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
    return view, embedding


def test_common_lifted_vertex_contacts_are_allowed() -> None:
    view, embedding = _manual_view_embedding(
        (
            (Fraction(0), Fraction(0), Fraction(0)),
            (Fraction(1, 2), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(1, 2), Fraction(0)),
        ),
        ((0, 1, (0, 0, 0), "a"), (0, 2, (0, 0, 0), "b")),
    )
    certificate = certify_periodic_straight_edge_embedding(view, embedding)
    assert certificate.status is PeriodicEdgeIntersectionStatus.CERTIFIED_INTERSECTION_FREE
    assert certificate.allowed_common_vertex_contact_count >= 1
    assert not certificate.forbidden_intersections


def test_nonincident_proper_crossing_is_rejected_exactly() -> None:
    view, embedding = _manual_view_embedding(
        (
            (Fraction(0), Fraction(0), Fraction(0)),
            (Fraction(1, 2), Fraction(1, 2), Fraction(0)),
            (Fraction(0), Fraction(1, 2), Fraction(0)),
            (Fraction(1, 2), Fraction(0), Fraction(0)),
        ),
        ((0, 1, (0, 0, 0), "a"), (2, 3, (0, 0, 0), "b")),
    )
    certificate = certify_periodic_straight_edge_embedding(view, embedding)
    assert certificate.status is PeriodicEdgeIntersectionStatus.FORBIDDEN_INTERSECTIONS_FOUND
    crossing = certificate.forbidden_intersections[0]
    assert crossing.contact_kind is PeriodicEdgeContactKind.FORBIDDEN_PROPER_CROSSING
    assert crossing.point_fractional == (Fraction(1, 4), Fraction(1, 4), Fraction(0))
    assert crossing.left_parameter_interval == (Fraction(1, 2), Fraction(1, 2))


def test_nonzero_periodic_image_crossing_is_found() -> None:
    view, embedding = _manual_view_embedding(
        (
            (Fraction(0), Fraction(0), Fraction(0)),
            (Fraction(1, 2), Fraction(1, 2), Fraction(0)),
            (Fraction(0), Fraction(3, 2), Fraction(0)),
            (Fraction(1, 2), Fraction(1), Fraction(0)),
        ),
        ((0, 1, (0, 0, 0), "a"), (2, 3, (0, 0, 0), "b")),
    )
    certificate = certify_periodic_straight_edge_embedding(
        view, embedding, method=PeriodicSpatialMethod.LINKED_CELL
    )
    crossing = next(
        item
        for item in certificate.forbidden_intersections
        if item.contact_kind is PeriodicEdgeContactKind.FORBIDDEN_PROPER_CROSSING
    )
    assert crossing.relative_image_shift == (0, -1, 0)


def test_collinear_overlap_is_distinct_from_endpoint_contact() -> None:
    view, embedding = _manual_view_embedding(
        (
            (Fraction(0), Fraction(0), Fraction(0)),
            (Fraction(3, 4), Fraction(0), Fraction(0)),
            (Fraction(1, 4), Fraction(0), Fraction(0)),
            (Fraction(1), Fraction(0), Fraction(0)),
        ),
        ((0, 1, (0, 0, 0), "a"), (2, 3, (0, 0, 0), "b")),
    )
    certificate = certify_periodic_straight_edge_embedding(view, embedding)
    assert any(
        item.contact_kind is PeriodicEdgeContactKind.FORBIDDEN_COLLINEAR_OVERLAP
        for item in certificate.forbidden_intersections
    )


def test_certificate_round_trip_replays_exact_sources() -> None:
    view, embedding = _manual_view_embedding(
        (
            (Fraction(0), Fraction(0), Fraction(0)),
            (Fraction(1, 2), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(1, 2), Fraction(0)),
        ),
        ((0, 1, (0, 0, 0), "a"), (0, 2, (0, 0, 0), "b")),
    )
    certificate = certify_periodic_straight_edge_embedding(
        view, embedding, method=PeriodicSpatialMethod.LINKED_CELL
    )
    payload = json.loads(json.dumps(certificate.to_dict()))
    restored = PeriodicEdgeIntersectionCertificate.from_dict(
        payload, view=view, embedding=embedding
    )
    assert restored == certificate
    payload["allowed_common_vertex_contact_count"] += 1
    payload["digest"] = "0" * 64
    with pytest.raises((PeriodicEdgeIntersectionSerializationError, ValueError)):
        PeriodicEdgeIntersectionCertificate.from_dict(
            payload, view=view, embedding=embedding
        )


def test_na_lta_straight_edge_embedding_is_globally_certified() -> None:
    topology = FrameworkTopology.from_dict(
        json.loads(
            (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
        )
    )
    view = build_periodic_net_view(topology)
    discovery = discover_periodic_net_symmetry(view)
    embedding = build_periodic_net_embedding(view, discovery)
    certificate = certify_periodic_straight_edge_embedding(view, embedding)

    assert certificate.status is PeriodicEdgeIntersectionStatus.CERTIFIED_INTERSECTION_FREE
    assert certificate.edge_count == view.n_edges
    assert certificate.candidate_count > 0
    assert certificate.allowed_common_vertex_contact_count > 0
