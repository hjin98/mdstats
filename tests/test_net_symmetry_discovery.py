from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from mdstats.analysis import (
    BARYCENTRIC_STAR_DISCOVERY_METHOD,
    BarycentricFrameIncidence,
    FrameworkEdgeKey,
    FrameworkTopology,
    NetSymmetryDiscoveryOptions,
    NetSymmetryDiscoveryResourceError,
    NetSymmetryDiscoveryUnsupportedError,
    NetViewPolicy,
    PeriodicNetComponent,
    PeriodicNetSymmetryDiscovery,
    PeriodicNetView,
    PrimitiveRingOptions,
    build_periodic_net_view,
    build_primitive_ring_index,
    discover_periodic_net_symmetry,
    enumerate_primitive_rings,
)


def diamond_view(*, decorated_vertices: bool = False) -> PeriodicNetView:
    shifts = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    edge_keys = tuple(
        sorted(
            FrameworkEdgeKey(0, 1, shift, (), (), f"edge-{position}")
            for position, shift in enumerate(shifts)
        )
    )
    component = PeriodicNetComponent(
        component_id=0,
        vertex_positions=(0, 1),
        edge_positions=tuple(range(4)),
        cycle_gain_generators=((0, 0, 1), (0, 1, 0), (1, 0, 0)),
        translation_rank=3,
        translation_index=1,
    )
    if decorated_vertices:
        vertex_signatures = (
            ("framework_vertex", "atomic_number", 14),
            ("framework_vertex", "atomic_number", 13),
        )
    else:
        vertex_signatures = (("framework_vertex",), ("framework_vertex",))
    return PeriodicNetView(
        source_graph_digest="a" * 64,
        source_topology_digest="b" * 64,
        pbc=(True, True, True),
        policy=NetViewPolicy.unlabeled_framework_net(),
        vertex_atom_indices=(0, 1),
        edge_keys=edge_keys,
        vertex_signatures=vertex_signatures,
        edge_signatures=(("framework_edge",),) * 4,
        components=(component,),
    )


def collided_view() -> PeriodicNetView:
    shifts = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    keys = []
    for target in (1, 2):
        for position, shift in enumerate(shifts):
            keys.append(
                FrameworkEdgeKey(
                    0,
                    target,
                    shift,
                    (),
                    (),
                    f"target-{target}-edge-{position}",
                )
            )
    edge_keys = tuple(sorted(keys))
    component = PeriodicNetComponent(
        component_id=0,
        vertex_positions=(0, 1, 2),
        edge_positions=tuple(range(8)),
        cycle_gain_generators=((0, 0, 1), (0, 1, 0), (1, 0, 0)),
        translation_rank=3,
        translation_index=1,
    )
    return PeriodicNetView(
        source_graph_digest="c" * 64,
        source_topology_digest="d" * 64,
        pbc=(True, True, True),
        policy=NetViewPolicy.unlabeled_framework_net(),
        vertex_atom_indices=(0, 1, 2),
        edge_keys=edge_keys,
        vertex_signatures=(("framework_vertex",),) * 3,
        edge_signatures=(("framework_edge",),) * 8,
        components=(component,),
    )


def test_exact_diamond_discovery_and_policy_restriction() -> None:
    unlabeled = discover_periodic_net_symmetry(diamond_view())
    decorated = discover_periodic_net_symmetry(
        diamond_view(decorated_vertices=True)
    )

    assert unlabeled.method == BARYCENTRIC_STAR_DISCOVERY_METHOD
    assert unlabeled.symmetry.order == 48
    assert decorated.symmetry.order == 24
    assert unlabeled.candidate_operation_count == 48
    assert decorated.candidate_operation_count == 24
    assert len(unlabeled.generators) == 4
    assert unlabeled.barycentric_placement.coordinates == (
        (Fraction(0), Fraction(0), Fraction(0)),
        (Fraction(-1, 4), Fraction(-1, 4), Fraction(-1, 4)),
    )
    assert len(unlabeled.source_frame) == 3
    assert all(isinstance(item, BarycentricFrameIncidence) for item in unlabeled.source_frame)
    assert any(
        shift != (0, 0, 0)
        for row in unlabeled.symmetry.composition_translation_table
        for shift in row
    )


def test_discovery_is_deterministic_and_serializable() -> None:
    view = diamond_view()
    first = discover_periodic_net_symmetry(view)
    second = discover_periodic_net_symmetry(view)
    assert first == second
    assert first.digest == second.digest
    payload = json.loads(json.dumps(first.to_dict()))
    assert PeriodicNetSymmetryDiscovery.from_dict(payload, view=view) == first


def test_collision_and_resource_limits_fail_transactionally() -> None:
    with pytest.raises(NetSymmetryDiscoveryUnsupportedError, match="collision"):
        discover_periodic_net_symmetry(collided_view())

    with pytest.raises(NetSymmetryDiscoveryResourceError, match="max_frame_trials"):
        discover_periodic_net_symmetry(
            diamond_view(),
            options=NetSymmetryDiscoveryOptions(max_frame_trials=1),
        )


def test_partial_periodic_view_is_outside_first_backend() -> None:
    view = diamond_view()
    partial = PeriodicNetView(
        source_graph_digest=view.source_graph_digest,
        source_topology_digest=view.source_topology_digest,
        pbc=(True, True, False),
        policy=view.policy,
        vertex_atom_indices=view.vertex_atom_indices,
        edge_keys=view.edge_keys,
        vertex_signatures=view.vertex_signatures,
        edge_signatures=view.edge_signatures,
        components=view.components,
    )
    with pytest.raises(NetSymmetryDiscoveryUnsupportedError, match="three-periodic"):
        discover_periodic_net_symmetry(partial)


def test_na_lta_discovers_full_group_and_ring_action() -> None:
    topology = FrameworkTopology.from_dict(
        json.loads(
            (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
        )
    )
    view = build_periodic_net_view(topology)
    ring_index = build_primitive_ring_index(
        enumerate_primitive_rings(
            topology,
            options=PrimitiveRingOptions(max_ring_size=8),
        )
    )
    result = discover_periodic_net_symmetry(view, ring_index=ring_index)

    assert result.symmetry.order == 96
    assert len(result.symmetry.vertex_orbits) == 1
    assert len(result.symmetry.edge_orbits) == 3
    assert result.ring_symmetry is not None
    assert sorted(len(orbit) for orbit in result.ring_symmetry.ring_orbits) == [6, 12, 16, 24, 24]
    assert sum(len(orbit) for orbit in result.ring_symmetry.ring_orbits) == 82
    assert any(
        shift != (0, 0, 0)
        for row in result.symmetry.composition_translation_table
        for shift in row
    )
