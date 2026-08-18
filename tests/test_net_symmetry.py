from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    ExplicitConnectivity,
    FrameworkAtomRole,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    LiftedVertexRef,
    NetSymmetryResourceError,
    NetSymmetrySerializationError,
    NetSymmetryValidationError,
    NetViewPolicy,
    PeriodicEdgeImage,
    PeriodicNetSymmetry,
    PeriodicRingActionValidationError,
    PrimitiveRingOptions,
    RingPlacement,
    build_atomic_connectivity_state,
    build_framework_topology,
    build_periodic_net_symmetry,
    build_primitive_ring_symmetry_index,
    build_periodic_net_view,
    build_primitive_ring_index,
    build_validated_periodic_automorphism,
    compose_periodic_automorphisms,
    enumerate_primitive_rings,
    identity_periodic_automorphism,
    invert_periodic_automorphism,
    normalize_periodic_automorphism,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics


ZERO = (0, 0, 0)
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
    *,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> FrameworkTopology:
    collection = make_collection([14] * n_vertices, pbc=pbc)
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


def action_from_permutation(view, permutation: dict[int, int], *, translation=ZERO):
    return build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={
            source: LiftedVertexRef(target, translation)
            for source, target in permutation.items()
        },
        edge_images=edge_images_from_vertex_permutation(view, permutation),
    )


def triangle_fixture():
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    view = build_periodic_net_view(topology)
    rotation = action_from_permutation(view, {0: 1, 1: 2, 2: 0})
    reflection = action_from_permutation(view, {0: 0, 1: 2, 2: 1})
    return topology, view, rotation, reflection


def test_identity_only_group_and_common_translation_normalization() -> None:
    topology, view, _rotation, _reflection = triangle_fixture()
    translated_identity = build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={
            atom: LiftedVertexRef(atom, (3, -2, 1))
            for atom in view.vertex_atom_indices
        },
        edge_images=tuple(
            PeriodicEdgeImage(position, 1) for position in range(view.n_edges)
        ),
    )
    normalized = normalize_periodic_automorphism(view, translated_identity)
    identity = identity_periodic_automorphism(view)
    assert normalized == identity

    group = build_periodic_net_symmetry(view, ())
    assert group.order == 1
    assert group.operations == (identity,)
    assert group.multiplication_table == ((0,),)
    assert group.inverse_operation_indices == (0,)
    assert group.vertex_orbits == ((0,), (1,), (2,))
    assert len(group.edge_orbits) == 3
    assert topology.graph_digest == group.topology_graph_digest


def test_triangle_rotation_and_reflection_generate_d3_exactly() -> None:
    _topology, view, rotation, reflection = triangle_fixture()
    group = build_periodic_net_symmetry(view, (rotation, reflection))

    assert group.order == 6
    assert group.vertex_orbits == ((0, 1, 2),)
    assert len(group.edge_orbits) == 1
    assert len(group.edge_orbits[0]) == 3
    assert all(
        group.compose_indices(i, group.inverse_index(i))
        == group.identity_operation_index
        for i in range(group.order)
    )

    normalized_rotation = normalize_periodic_automorphism(view, rotation)
    rotation_index = group.operations.index(normalized_rotation)
    squared = group.compose_indices(rotation_index, rotation_index)
    cubed = group.compose_indices(rotation_index, squared)
    assert cubed == group.identity_operation_index

    normalized_reflection = normalize_periodic_automorphism(view, reflection)
    reflection_index = group.operations.index(normalized_reflection)
    assert (
        group.compose_indices(reflection_index, reflection_index)
        == group.identity_operation_index
    )
    assert group.compose_indices(rotation_index, reflection_index) != group.compose_indices(
        reflection_index, rotation_index
    )


def test_composition_convention_and_exact_inverse_with_lattice_action() -> None:
    topology = direct_topology(
        3,
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(0, 2)),
    )
    view = build_periodic_net_view(topology)
    inversion = build_validated_periodic_automorphism(
        view,
        lattice_matrix=NEGATIVE_IDENTITY,
        vertex_images={atom: LiftedVertexRef(atom, ZERO) for atom in view.vertex_atom_indices},
        edge_images=tuple(
            PeriodicEdgeImage(position, 1) for position in range(view.n_edges)
        ),
    )
    inverse = invert_periodic_automorphism(view, inversion)
    assert inverse == normalize_periodic_automorphism(view, inversion)
    product = compose_periodic_automorphisms(view, inversion, inverse)
    assert product == identity_periodic_automorphism(view)


def test_generator_order_does_not_change_canonical_group_digest() -> None:
    _topology, view, rotation, reflection = triangle_fixture()
    first = build_periodic_net_symmetry(view, (rotation, reflection))
    second = build_periodic_net_symmetry(view, (reflection, rotation, rotation))
    assert first == second
    assert first.digest == second.digest
    assert first.operations == second.operations


def test_parallel_edge_exchange_forms_order_two_group() -> None:
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
    topology = build_framework_topology(state, mapping)
    view = build_periodic_net_view(topology)
    swap = build_validated_periodic_automorphism(
        view,
        lattice_matrix=IDENTITY,
        vertex_images={0: LiftedVertexRef(0, ZERO), 1: LiftedVertexRef(1, ZERO)},
        edge_images=(PeriodicEdgeImage(1, 1), PeriodicEdgeImage(0, 1)),
    )
    group = build_periodic_net_symmetry(view, (swap,))
    assert group.order == 2
    assert group.edge_orbits == ((view.edge_keys[0], view.edge_keys[1]),)


def test_ring_action_orbits_stabilizers_and_homomorphism() -> None:
    topology, view, rotation, reflection = triangle_fixture()
    index = build_index(topology)
    group = build_periodic_net_symmetry(view, (rotation, reflection))
    ring_symmetry = build_primitive_ring_symmetry_index(view, group, index)
    assert len(ring_symmetry.ring_keys) == 1
    assert ring_symmetry.ring_orbits == ((0,),)
    assert ring_symmetry.ring_stabilizers == (tuple(range(group.order)),)
    assert len(ring_symmetry.action_table) == group.order
    for operation_index in range(group.order):
        image = ring_symmetry.ring_image(
            operation_index, ring_symmetry.ring_keys[0]
        )
        assert ring_symmetry.target_ring_key(image) == ring_symmetry.ring_keys[0]


def test_two_triangle_exchange_builds_nontrivial_ring_orbit() -> None:
    topology = direct_topology(
        6,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(3, 4),
            AtomicEdgeKey(4, 5),
            AtomicEdgeKey(3, 5),
        ),
    )
    view = build_periodic_net_view(topology)
    index = build_index(topology)
    swap_permutation = {0: 3, 1: 4, 2: 5, 3: 0, 4: 1, 5: 2}
    swap = action_from_permutation(view, swap_permutation)
    group = build_periodic_net_symmetry(view, (swap,))
    ring_symmetry = build_primitive_ring_symmetry_index(view, group, index)
    assert group.order == 2
    assert len(ring_symmetry.ring_keys) == 2
    assert ring_symmetry.ring_orbits == ((0, 1),)
    assert all(len(stabilizer) == 1 for stabilizer in ring_symmetry.ring_stabilizers)


def test_serialization_round_trip_and_view_mismatch_rejection() -> None:
    topology, view, rotation, reflection = triangle_fixture()
    index = build_index(topology)
    group = build_periodic_net_symmetry(view, (rotation, reflection))
    payload = json.loads(json.dumps(group.to_dict()))
    restored = PeriodicNetSymmetry.from_dict(payload, view=view)
    assert restored == group
    assert restored.to_dict() == group.to_dict()

    decorated = build_periodic_net_view(
        topology, policy=NetViewPolicy.chemically_decorated()
    )
    with pytest.raises(NetSymmetrySerializationError, match="source digests"):
        PeriodicNetSymmetry.from_dict(payload, view=decorated)

    tampered = json.loads(json.dumps(payload))
    tampered["composition_translation_table"][0][0] = [1, 0, 0]
    with pytest.raises(NetSymmetrySerializationError, match="not canonical"):
        PeriodicNetSymmetry.from_dict(tampered, view=view)

    bad_table = [list(row) for row in group.composition_translation_table]
    bad_table[0][0] = (1, 0, 0)
    with pytest.raises(
        NetSymmetryValidationError, match="composition_translation_table"
    ):
        replace(
            group,
            composition_translation_table=tuple(tuple(row) for row in bad_table),
            digest="",
        )


def test_nonperiodic_vertex_image_shift_is_rejected() -> None:
    topology = direct_topology(
        2,
        (AtomicEdgeKey(0, 1, (1, 0, 0)),),
        pbc=(True, False, False),
    )
    view = build_periodic_net_view(topology)
    with pytest.raises(PeriodicRingActionValidationError, match="nonperiodic axes"):
        build_validated_periodic_automorphism(
            view,
            lattice_matrix=IDENTITY,
            vertex_images={
                0: LiftedVertexRef(0, (0, 1, 0)),
                1: LiftedVertexRef(1, (0, 1, 0)),
            },
            edge_images=(PeriodicEdgeImage(0, 1),),
        )



def test_square_rotation_and_reflection_generate_d4_with_ring_stabilizer() -> None:
    topology = direct_topology(
        4,
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(0, 3),
        ),
    )
    view = build_periodic_net_view(topology)
    index = build_index(topology)
    rotation = action_from_permutation(view, {0: 1, 1: 2, 2: 3, 3: 0})
    reflection = action_from_permutation(view, {0: 0, 1: 3, 2: 2, 3: 1})
    group = build_periodic_net_symmetry(view, (rotation, reflection))
    ring_symmetry = build_primitive_ring_symmetry_index(view, group, index)
    assert group.order == 8
    assert group.vertex_orbits == ((0, 1, 2, 3),)
    assert len(ring_symmetry.ring_keys) == 1
    assert ring_symmetry.ring_stabilizers == (tuple(range(8)),)


def test_na_lta_identity_group_covers_all_82_ring_orbits() -> None:
    from pathlib import Path

    payload = json.loads(
        (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
    )
    topology = FrameworkTopology.from_dict(payload)
    view = build_periodic_net_view(topology)
    index = build_index(topology)
    group = build_periodic_net_symmetry(view, ())
    ring_symmetry = build_primitive_ring_symmetry_index(view, group, index)
    assert group.order == 1
    assert len(ring_symmetry.ring_keys) == 82
    assert sum(len(key.edge_tokens) for key in ring_symmetry.ring_keys) == 432
    assert len(ring_symmetry.ring_orbits) == 82
    assert all(stabilizer == (0,) for stabilizer in ring_symmetry.ring_stabilizers)

def test_operation_limit_rejects_unbounded_shear_closure_transactionally() -> None:
    topology = direct_topology(1, ())
    view = build_periodic_net_view(topology)
    shear = build_validated_periodic_automorphism(
        view,
        lattice_matrix=((1, 1, 0), (0, 1, 0), (0, 0, 1)),
        vertex_images={0: LiftedVertexRef(0, ZERO)},
        edge_images=(),
    )
    with pytest.raises(NetSymmetryResourceError, match="max_operations"):
        build_periodic_net_symmetry(view, (shear,), max_operations=5)
