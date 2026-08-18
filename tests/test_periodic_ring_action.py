from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    ExplicitConnectivity,
    FrameworkAtomRole,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    LiftedEdgeInstanceRef,
    LiftedVertexRef,
    NetViewPolicy,
    PeriodicEdgeImage,
    PeriodicRingActionInputError,
    PeriodicRingActionValidationError,
    PrimitiveRingOptions,
    RingPlacement,
    build_atomic_connectivity_state,
    build_framework_topology,
    build_periodic_net_view,
    build_primitive_ring_index,
    build_validated_periodic_automorphism,
    enumerate_primitive_rings,
    map_lifted_edge_instance,
    map_lifted_vertex,
    map_ring_placement,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics


ZERO = (0, 0, 0)


def rp(index, key, shift):
    return RingPlacement(index.topology_graph_digest, key, shift)
IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
NEGATIVE_IDENTITY = ((-1, 0, 0), (0, -1, 0), (0, 0, -1))


def make_collection(
    atomic_numbers: list[int],
    *,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> AtomisticFrameCollection:
    n_atoms = len(atomic_numbers)
    cell = np.eye(3) * 10.0
    positions = np.arange(n_atoms * 3, dtype=float).reshape(n_atoms, 3) * 0.1
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.asarray(pbc, dtype=bool),
        steps=None,
        times=None,
        cells=cell[None, ...],
        origins=np.zeros((1, 3)),
        fractional_positions=(positions @ np.linalg.inv(cell))[None, ...],
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


def direct_topology(
    n_vertices: int,
    edges: tuple[AtomicEdgeKey, ...],
) -> FrameworkTopology:
    collection = make_collection([14] * n_vertices)
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(uniform_edges=edges),
        frame_index=0,
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": FrameworkAtomRole.VERTEX},
        path_rules=(FrameworkPathRule("direct", (), edge_kind="direct"),),
        name="direct graph",
    )
    return build_framework_topology(state, mapping)


def build_index(topology: FrameworkTopology):
    return build_primitive_ring_index(
        enumerate_primitive_rings(
            topology,
            options=PrimitiveRingOptions(max_ring_size=8),
        )
    )


def identity_action(index, view, *, translation=ZERO, lattice_matrix=IDENTITY):
    vertices = sorted(
        {
            vertex
            for edge_search in index.catalog.edge_searches
            for vertex in (
                edge_search.edge_key.vertex_i,
                edge_search.edge_key.vertex_j,
            )
        }
    )
    return build_validated_periodic_automorphism(
        view,
        lattice_matrix=lattice_matrix,
        vertex_images={
            vertex: LiftedVertexRef(vertex, translation) for vertex in vertices
        },
        edge_images=tuple(
            PeriodicEdgeImage(edge_index, 1)
            for edge_index in range(len(index.catalog.edge_searches))
        ),
    )


def edge_images_from_vertex_permutation(view, permutation: dict[int, int]):
    by_endpoints: dict[tuple[int, int], int] = {}
    for edge_index, key in enumerate(view.edge_keys):
        assert key.image_shift == ZERO
        by_endpoints[(key.vertex_i, key.vertex_j)] = edge_index
    result = []
    for key in view.edge_keys:
        mapped_i = permutation[key.vertex_i]
        mapped_j = permutation[key.vertex_j]
        endpoints = tuple(sorted((mapped_i, mapped_j)))
        target = by_endpoints[endpoints]
        orientation = 1 if (mapped_i, mapped_j) == endpoints else -1
        result.append(PeriodicEdgeImage(target, orientation))
    return tuple(result)


def test_identity_and_common_translation_map_exact_occurrences() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    ring = index.catalog.rings[0]
    action = identity_action(index, view, translation=(2, -1, 3))
    source = rp(index, ring.key, (4, 5, -2))
    mapped = map_ring_placement(index, view, action, source)

    assert mapped.target_placement == rp(index, ring.key, (6, 4, 1))
    assert mapped.source_vertex_position_to_target_position == tuple(range(ring.size))
    assert mapped.source_step_position_to_target_position == tuple(range(ring.size))
    assert mapped.orientation == 1
    assert mapped.start_vertex_index == 0


def test_unimodular_lattice_action_transforms_ring_translation() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    ring = index.catalog.rings[0]
    action = identity_action(index, view, lattice_matrix=NEGATIVE_IDENTITY)
    source = rp(index, ring.key, (2, -3, 4))
    mapped = map_ring_placement(index, view, action, source)

    assert mapped.target_placement == rp(index, ring.key, (-2, 3, -4))
    assert map_lifted_vertex(action, LiftedVertexRef(0, (1, 2, -1))) == LiftedVertexRef(
        0, (-1, -2, 1)
    )


def test_square_rotation_produces_exact_nontrivial_occurrence_permutations() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    ring = index.catalog.rings[0]
    permutation = {0: 1, 1: 2, 2: 3, 3: 0}
    action = build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={
            source: LiftedVertexRef(target, ZERO)
            for source, target in permutation.items()
        },
        edge_images=edge_images_from_vertex_permutation(view, permutation),
    )
    mapped = map_ring_placement(index, view, action, rp(index, ring.key, ZERO))

    assert mapped.target_placement.ring_key == ring.key
    assert mapped.source_vertex_position_to_target_position != tuple(range(ring.size))
    for source_position, target_position in enumerate(
        mapped.source_vertex_position_to_target_position
    ):
        source_vertex = ring.vertex_walk[source_position]
        target_vertex = ring.vertex_walk[target_position]
        assert permutation[source_vertex.atom_index] == target_vertex.atom_index


def test_square_reflection_recovers_reversed_boundary_orientation() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    ring = index.catalog.rings[0]
    permutation = {0: 0, 1: 3, 2: 2, 3: 1}
    action = build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={
            source: LiftedVertexRef(target, ZERO)
            for source, target in permutation.items()
        },
        edge_images=edge_images_from_vertex_permutation(view, permutation),
    )
    mapped = map_ring_placement(index, view, action, rp(index, ring.key, ZERO))

    assert mapped.target_placement.ring_key == ring.key
    assert mapped.orientation == -1
    assert mapped.source_vertex_position_to_target_position == tuple(
        (mapped.start_vertex_index - k) % ring.size for k in range(ring.size)
    )


def test_explicit_parallel_edge_permutation_is_authoritative() -> None:
    collection = make_collection([14, 14, 8, 8])
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(
            uniform_edges=(
                AtomicEdgeKey(0, 2),
                AtomicEdgeKey(1, 2),
                AtomicEdgeKey(0, 3),
                AtomicEdgeKey(1, 3),
            )
        ),
        frame_index=0,
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",)),),
        name="parallel linker graph",
    )
    topology = build_framework_topology(state, mapping)
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    ring = index.catalog.rings[0]
    assert ring.size == 2
    assert len(index.catalog.edge_searches) == 2

    action = build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={0: LiftedVertexRef(0, ZERO), 1: LiftedVertexRef(1, ZERO)},
        edge_images=(PeriodicEdgeImage(1, 1), PeriodicEdgeImage(0, 1)),
    )
    mapped = map_ring_placement(index, view, action, rp(index, ring.key, ZERO))

    assert mapped.target_placement.ring_key == ring.key
    assert mapped.source_step_position_to_target_position != (0, 1)
    first = index.canonical_edge_instance(ring.key, 0)
    mapped_first = map_lifted_edge_instance(view, action, first)
    assert mapped_first.edge_key == index.edge_key_for_index(1 - index.edge_index_for_key(first.edge_key))



def test_repeated_rotation_matches_direct_composed_vertex_action() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    ring = index.catalog.rings[0]
    quarter = {0: 1, 1: 2, 2: 3, 3: 0}
    half = {0: 2, 1: 3, 2: 0, 3: 1}
    quarter_action = build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={
            source: LiftedVertexRef(target, ZERO)
            for source, target in quarter.items()
        },
        edge_images=edge_images_from_vertex_permutation(view, quarter),
    )
    half_action = build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={
            source: LiftedVertexRef(target, ZERO)
            for source, target in half.items()
        },
        edge_images=edge_images_from_vertex_permutation(view, half),
    )

    first = map_ring_placement(index, view, quarter_action, rp(index, ring.key, ZERO))
    second = map_ring_placement(index, view, quarter_action, first.target_placement)
    direct = map_ring_placement(index, view, half_action, rp(index, ring.key, ZERO))

    assert second.target_placement == direct.target_placement
    # Because both maps use the same canonical source/target ring here, composing
    # source-position maps reduces to second[first[k]].
    composed_vertex_permutation = tuple(
        second.source_vertex_position_to_target_position[
            first.source_vertex_position_to_target_position[k]
        ]
        for k in range(ring.size)
    )
    composed_step_permutation = tuple(
        second.source_step_position_to_target_position[first.source_step_position_to_target_position[k]]
        for k in range(ring.size)
    )
    assert composed_vertex_permutation == direct.source_vertex_position_to_target_position
    assert composed_step_permutation == direct.source_step_position_to_target_position

def test_invalid_edge_action_is_rejected_even_if_vertex_map_is_a_permutation() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    with pytest.raises(PeriodicRingActionValidationError, match="inconsistent"):
        build_validated_periodic_automorphism(
            view,
            lattice_matrix=IDENTITY,
            vertex_images={
                0: LiftedVertexRef(0, ZERO),
                1: LiftedVertexRef(1, ZERO),
                2: LiftedVertexRef(2, ZERO),
            },
            edge_images=(
                PeriodicEdgeImage(1, 1),
                PeriodicEdgeImage(0, 1),
                PeriodicEdgeImage(2, 1),
            ),
        )


def test_source_digest_mismatch_is_rejected() -> None:
    triangle_topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    square_topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    triangle = build_index(triangle_topology)
    square = build_index(square_topology)
    triangle_view = build_periodic_net_view(triangle_topology)
    square_view = build_periodic_net_view(square_topology)
    action = identity_action(triangle, triangle_view)
    with pytest.raises(PeriodicRingActionInputError, match="different PeriodicNetView|different topology"):
        map_ring_placement(
            square,
            square_view,
            action,
            rp(square, square.catalog.rings[0].key, ZERO),
        )


def test_na_lta_identity_translation_maps_all_82_ring_orbits_and_432_steps() -> None:
    payload = json.loads(
        (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
    )
    topology = FrameworkTopology.from_dict(payload)
    index = build_index(topology)
    view = build_periodic_net_view(topology)
    translation = (3, -2, 1)
    action = identity_action(index, view, translation=translation)

    assert len(index.catalog.rings) == 82
    assert sum(ring.size for ring in index.catalog.rings) == 432
    for ring in index.catalog.rings:
        mapped = map_ring_placement(index, view, action, rp(index, ring.key, ZERO))
        assert mapped.target_placement == rp(index, ring.key, translation)
        assert mapped.source_vertex_position_to_target_position == tuple(range(ring.size))
        assert mapped.source_step_position_to_target_position == tuple(range(ring.size))
        assert mapped.orientation == 1
        for step_index in range(ring.size):
            source_edge = index.canonical_edge_instance(ring.key, step_index)
            mapped_edge = map_lifted_edge_instance(view, action, source_edge)
            assert mapped_edge == LiftedEdgeInstanceRef(
                index.topology_graph_digest,
                source_edge.edge_key,
                tuple(
                    a + b
                    for a, b in zip(
                        source_edge.anchor_shift, translation, strict=True
                    )
                ),
            )


def direct_topology_with_atomic_numbers(
    atomic_numbers: list[int],
    edges: tuple[AtomicEdgeKey, ...],
    *,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> FrameworkTopology:
    collection = make_collection(atomic_numbers, pbc=pbc)
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(uniform_edges=edges),
        frame_index=0,
    )
    roles = {"Si": FrameworkAtomRole.VERTEX}
    if 13 in atomic_numbers:
        roles["Al"] = FrameworkAtomRole.VERTEX
    mapping = FrameworkMapping.from_symbol_roles(
        roles,
        path_rules=(FrameworkPathRule("direct", (), edge_kind="direct"),),
        name="decorated direct graph",
    )
    return build_framework_topology(state, mapping)


def parallel_oxygen_sulfur_topology() -> FrameworkTopology:
    collection = make_collection([14, 14, 8, 16])
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(
            uniform_edges=(
                AtomicEdgeKey(0, 2),
                AtomicEdgeKey(1, 2),
                AtomicEdgeKey(0, 3),
                AtomicEdgeKey(1, 3),
            )
        ),
        frame_index=0,
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "S": FrameworkAtomRole.LINKER,
        },
        path_rules=(
            FrameworkPathRule.from_symbols("oxygen", ("O",), edge_kind="bridge"),
            FrameworkPathRule.from_symbols("sulfur", ("S",), edge_kind="bridge"),
        ),
        name="parallel decorated linker graph",
    )
    return build_framework_topology(state, mapping)


def test_unlabeled_view_allows_vertex_exchange_rejected_by_chemical_view() -> None:
    topology = direct_topology_with_atomic_numbers(
        [14, 13],
        (AtomicEdgeKey(0, 1),),
    )
    unlabeled = build_periodic_net_view(topology)
    decorated = build_periodic_net_view(
        topology, policy=NetViewPolicy.chemically_decorated()
    )
    kwargs = dict(
        lattice_matrix=IDENTITY,
        vertex_images={
            0: LiftedVertexRef(1, ZERO),
            1: LiftedVertexRef(0, ZERO),
        },
        edge_images=(PeriodicEdgeImage(0, -1),),
    )

    action = build_validated_periodic_automorphism(unlabeled, **kwargs)
    assert action.periodic_net_view_digest == unlabeled.digest
    with pytest.raises(PeriodicRingActionValidationError, match="Vertex action violates"):
        build_validated_periodic_automorphism(decorated, **kwargs)


def test_unlabeled_view_allows_parallel_edge_exchange_rejected_by_chemical_view() -> None:
    topology = parallel_oxygen_sulfur_topology()
    unlabeled = build_periodic_net_view(topology)
    decorated = build_periodic_net_view(
        topology, policy=NetViewPolicy.chemically_decorated()
    )
    kwargs = dict(
        lattice_matrix=IDENTITY,
        vertex_images={
            0: LiftedVertexRef(0, ZERO),
            1: LiftedVertexRef(1, ZERO),
        },
        edge_images=(PeriodicEdgeImage(1, 1), PeriodicEdgeImage(0, 1)),
    )

    build_validated_periodic_automorphism(unlabeled, **kwargs)
    with pytest.raises(PeriodicRingActionValidationError, match="Edge action violates"):
        build_validated_periodic_automorphism(decorated, **kwargs)


def test_action_cannot_be_reused_under_another_view_of_same_topology() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    index = build_index(topology)
    ring = index.catalog.rings[0]
    unlabeled = build_periodic_net_view(topology)
    decorated = build_periodic_net_view(
        topology, policy=NetViewPolicy.chemically_decorated()
    )
    action = identity_action(index, unlabeled)

    with pytest.raises(PeriodicRingActionInputError, match="different PeriodicNetView"):
        map_ring_placement(
            index,
            decorated,
            action,
            rp(index, ring.key, ZERO),
        )


def test_lattice_matrix_must_preserve_active_pbc_subspace() -> None:
    topology = direct_topology_with_atomic_numbers(
        [14, 14],
        (AtomicEdgeKey(0, 1, (1, 0, 0)),),
        pbc=(True, False, False),
    )
    view = build_periodic_net_view(topology)
    swap_x_z = ((0, 0, 1), (0, 1, 0), (1, 0, 0))

    with pytest.raises(PeriodicRingActionValidationError, match="nonperiodic axes"):
        build_validated_periodic_automorphism(
            view,
            lattice_matrix=swap_x_z,
            vertex_images={
                0: LiftedVertexRef(0, ZERO),
                1: LiftedVertexRef(1, ZERO),
            },
            edge_images=(PeriodicEdgeImage(0, 1),),
        )
