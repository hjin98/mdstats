from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis import (
    FrameworkEdgeKey,
    FrameworkTopology,
    NetViewPolicy,
    PeriodicNetComponent,
    PeriodicNetEmbedding,
    NetSymmetryDiscoveryUnsupportedError,
    PeriodicNetEmbeddingResourceError,
    PeriodicNetEmbeddingResources,
    PeriodicNetEmbeddingSerializationError,
    PeriodicNetEmbeddingUnsupportedError,
    PeriodicNetView,
    build_periodic_net_embedding,
    build_periodic_net_view,
    discover_periodic_net_symmetry,
)
from tests.test_net_symmetry_discovery import collided_view, diamond_view


def _matvec(matrix: tuple[tuple[int, int, int], ...], vector: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    )


def sheared_diamond_view() -> PeriodicNetView:
    # Old coordinates satisfy x = P x', so shifts transform as x' = P^{-1} x.
    inverse_basis = ((1, -1, 0), (0, 1, 0), (0, 0, 1))
    old_shifts = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    shifts = tuple(_matvec(inverse_basis, shift) for shift in old_shifts)
    edge_keys = tuple(
        sorted(
            FrameworkEdgeKey(0, 1, shift, (), (), f"edge-{position}")
            for position, shift in enumerate(shifts)
        )
    )
    gains = tuple(
        sorted(
            {
                _matvec(inverse_basis, (1, 0, 0)),
                _matvec(inverse_basis, (0, 1, 0)),
                _matvec(inverse_basis, (0, 0, 1)),
            }
        )
    )
    component = PeriodicNetComponent(
        component_id=0,
        vertex_positions=(0, 1),
        edge_positions=tuple(range(4)),
        cycle_gain_generators=gains,
        translation_rank=3,
        translation_index=1,
    )
    return PeriodicNetView(
        source_graph_digest="e" * 64,
        source_topology_digest="f" * 64,
        pbc=(True, True, True),
        policy=NetViewPolicy.unlabeled_framework_net(),
        vertex_atom_indices=(0, 1),
        edge_keys=edge_keys,
        vertex_signatures=(("framework_vertex",),) * 2,
        edge_signatures=(("framework_edge",),) * 4,
        components=(component,),
    )


def coincident_parallel_diamond_view() -> PeriodicNetView:
    base = diamond_view()
    duplicate = FrameworkEdgeKey(0, 1, (0, 0, 0), (), (), "duplicate-edge")
    keys = tuple(sorted(base.edge_keys + (duplicate,)))
    component = PeriodicNetComponent(
        component_id=0,
        vertex_positions=(0, 1),
        edge_positions=tuple(range(len(keys))),
        cycle_gain_generators=base.components[0].cycle_gain_generators,
        translation_rank=3,
        translation_index=1,
    )
    return PeriodicNetView(
        source_graph_digest="1" * 64,
        source_topology_digest="2" * 64,
        pbc=(True, True, True),
        policy=base.policy,
        vertex_atom_indices=base.vertex_atom_indices,
        edge_keys=keys,
        vertex_signatures=base.vertex_signatures,
        edge_signatures=(("framework_edge",),) * len(keys),
        components=(component,),
    )


def test_diamond_embedding_has_exact_metric_and_cartesian_geometry() -> None:
    view = diamond_view()
    discovery = discover_periodic_net_symmetry(view)
    embedding = build_periodic_net_embedding(view, discovery)

    assert embedding.primitive_gram_matrix == (
        (2, 1, 1),
        (1, 2, 1),
        (1, 1, 2),
    )
    assert embedding.metric_determinant == 4
    assert embedding.minimum_edge_length_squared == Fraction(3, 4)
    assert embedding.maximum_edge_length_squared == Fraction(3, 4)
    assert np.isclose(np.linalg.det(embedding.unit_volume_gram_matrix()), 1.0)
    assert np.isclose(np.linalg.det(embedding.cell_matrix()), 1.0)
    assert embedding.fractional_coordinate(1, wrap=True) == (
        Fraction(3, 4),
        Fraction(3, 4),
        Fraction(3, 4),
    )

    gram = np.asarray(embedding.primitive_gram_matrix, dtype=int)
    coordinates = {
        atom: embedding.fractional_coordinates[position]
        for position, atom in enumerate(embedding.vertex_atom_indices)
    }
    anchor = discovery.symmetry.anchor_atom_index
    for operation in discovery.symmetry.operations:
        matrix = np.asarray(operation.lattice_matrix, dtype=int)
        assert np.array_equal(matrix.T @ gram @ matrix, gram)
        anchor_target = coordinates[operation.vertex_image(anchor).atom_index]
        for atom in embedding.vertex_atom_indices:
            image = operation.vertex_image(atom)
            transformed = tuple(
                sum(Fraction(operation.lattice_matrix[row][column]) * coordinates[atom][column] for column in range(3))
                + anchor_target[row]
                for row in range(3)
            )
            expected = tuple(
                coordinates[image.atom_index][axis] + image.image_shift[axis]
                for axis in range(3)
            )
            assert transformed == expected

    segment = embedding.edge_segment(view.edge_keys[0], anchor_shift=(2, -1, 0))
    assert segment.periodic_net_embedding_digest == embedding.digest
    assert segment.start_fractional == (Fraction(2), Fraction(-1), Fraction(0))
    assert segment.primitive_squared_length > 0


def test_metric_is_covariant_under_unimodular_basis_shear() -> None:
    original_view = diamond_view()
    sheared_view = sheared_diamond_view()
    original = build_periodic_net_embedding(
        original_view, discover_periodic_net_symmetry(original_view)
    )
    sheared = build_periodic_net_embedding(
        sheared_view, discover_periodic_net_symmetry(sheared_view)
    )

    basis = np.asarray(((1, 1, 0), (0, 1, 0), (0, 0, 1)), dtype=int)
    expected = basis.T @ np.asarray(original.primitive_gram_matrix, dtype=int) @ basis
    assert np.array_equal(np.asarray(sheared.primitive_gram_matrix), expected)


def test_embedding_round_trip_rebuilds_from_exact_sources() -> None:
    view = diamond_view()
    discovery = discover_periodic_net_symmetry(view)
    embedding = build_periodic_net_embedding(view, discovery)
    payload = json.loads(json.dumps(embedding.to_dict()))

    restored = PeriodicNetEmbedding.from_dict(
        payload, view=view, discovery=discovery
    )
    assert restored == embedding

    other_view = diamond_view(decorated_vertices=True)
    other_discovery = discover_periodic_net_symmetry(other_view)
    with pytest.raises(PeriodicNetEmbeddingSerializationError):
        PeriodicNetEmbedding.from_dict(
            payload, view=other_view, discovery=other_discovery
        )


def test_collisions_and_coincident_projected_edges_are_rejected() -> None:
    collided = collided_view()
    # Discovery rejects this earlier; use its established unsupported condition.
    with pytest.raises(NetSymmetryDiscoveryUnsupportedError, match="collision"):
        discover_periodic_net_symmetry(collided)

    parallel = coincident_parallel_diamond_view()
    discovery = discover_periodic_net_symmetry(parallel)
    with pytest.raises(PeriodicNetEmbeddingUnsupportedError, match="coincide"):
        build_periodic_net_embedding(parallel, discovery)


def test_embedding_resource_limits_are_transactional() -> None:
    view = diamond_view()
    discovery = discover_periodic_net_symmetry(view)
    with pytest.raises(PeriodicNetEmbeddingResourceError, match="max_edges"):
        build_periodic_net_embedding(
            view,
            discovery,
            resources=PeriodicNetEmbeddingResources(max_edges=1),
        )

    with pytest.raises(PeriodicNetEmbeddingResourceError, match="max_metric_fraction_bits"):
        build_periodic_net_embedding(
            view,
            discovery,
            resources=PeriodicNetEmbeddingResources(max_metric_fraction_bits=1),
        )


def test_na_lta_builds_authoritative_embedding_for_full_symmetry() -> None:
    topology = FrameworkTopology.from_dict(
        json.loads(
            (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
        )
    )
    view = build_periodic_net_view(topology)
    discovery = discover_periodic_net_symmetry(view)
    embedding = build_periodic_net_embedding(view, discovery)

    assert discovery.symmetry.order == 96
    assert embedding.n_vertices == view.n_vertices
    assert embedding.n_edges == view.n_edges
    assert embedding.metric_determinant > 0
    assert embedding.minimum_edge_length_squared > 0
    assert np.isclose(np.linalg.det(embedding.cell_matrix()), 1.0)
