from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from mdstats.analysis import (
    AtomicEdgeKey,
    EdgeSignatureField,
    ExplicitConnectivity,
    FrameworkAtomRole,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    NetViewPolicy,
    PeriodicNetView,
    PeriodicNetViewInputError,
    PeriodicNetViewSerializationError,
    VertexSignatureField,
    build_atomic_connectivity_state,
    build_framework_topology,
    build_periodic_net_view,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.provenance import FrameCollectionProvenance
from mdstats.semantics import FrameSemantics


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
        name="direct graph",
    )
    return build_framework_topology(state, mapping)


def periodic_cycle_topology(
    gains: tuple[tuple[int, int, int], ...],
    *,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> FrameworkTopology:
    """Build one connected quotient graph with one triangle per cycle gain."""
    atomic_numbers = [14] * (1 + 2 * len(gains))
    edges: list[AtomicEdgeKey] = []
    for cycle_index, gain in enumerate(gains):
        left = 1 + 2 * cycle_index
        right = left + 1
        edges.extend(
            (
                AtomicEdgeKey(0, left),
                AtomicEdgeKey(left, right),
                AtomicEdgeKey(0, right, gain),
            )
        )
    if not gains:
        atomic_numbers = [14, 14]
        edges = [AtomicEdgeKey(0, 1)]
    return direct_topology(atomic_numbers, tuple(edges), pbc=pbc)


def parallel_linker_topology() -> FrameworkTopology:
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
        name="parallel linker graph",
    )
    return build_framework_topology(state, mapping)


def test_unlabeled_and_decorated_signatures_preserve_source_graph() -> None:
    topology = direct_topology([14, 13], (AtomicEdgeKey(0, 1),))
    unlabeled = build_periodic_net_view(topology)
    decorated = build_periodic_net_view(
        topology, policy=NetViewPolicy.chemically_decorated()
    )

    assert unlabeled.vertex_atom_indices == tuple(topology.vertex_atom_indices)
    assert unlabeled.edge_keys == tuple(edge.key for edge in topology.edges)
    assert unlabeled.n_vertices == topology.n_vertices
    assert unlabeled.n_edges == topology.n_edges
    assert len(set(unlabeled.vertex_signatures)) == 1
    assert len(set(decorated.vertex_signatures)) == 2
    assert decorated.vertex_signatures[0] != decorated.vertex_signatures[1]
    assert unlabeled.digest != decorated.digest


def test_policy_semantics_are_independent_of_descriptive_label() -> None:
    left = NetViewPolicy.unlabeled_framework_net(label="T net")
    right = NetViewPolicy.unlabeled_framework_net(label="abstract framework")
    assert left.digest == right.digest
    assert left == right
    topology = periodic_cycle_topology(((1, 0, 0),))
    left_view = build_periodic_net_view(topology, policy=left)
    right_view = build_periodic_net_view(topology, policy=right)
    assert left_view.digest == right_view.digest
    assert left_view == right_view


def test_parallel_edges_remain_distinct_even_when_signatures_match() -> None:
    topology = parallel_linker_topology()
    view = build_periodic_net_view(topology)
    assert view.n_edges == 2
    assert len(set(view.edge_keys)) == 2
    assert len(set(view.edge_signatures)) == 1
    decorated = build_periodic_net_view(
        topology, policy=NetViewPolicy.chemically_decorated()
    )
    assert len(set(decorated.edge_signatures)) == 2
    assert decorated.edge_signature(decorated.edge_keys[0]) == decorated.edge_signatures[0]


def test_explicit_policy_fields_are_canonical_and_serializable() -> None:
    policy = NetViewPolicy(
        vertex_fields=(VertexSignatureField.ATOMIC_NUMBER,),
        edge_fields=(
            EdgeSignatureField.RULE_ID,
            EdgeSignatureField.EDGE_KIND,
            EdgeSignatureField.LINKER_COUNT,
        ),
        label="custom",
    )
    assert policy.edge_fields == (
        EdgeSignatureField.EDGE_KIND,
        EdgeSignatureField.LINKER_COUNT,
        EdgeSignatureField.RULE_ID,
    )
    assert NetViewPolicy.from_dict(json.loads(json.dumps(policy.to_dict()))) == policy
    with pytest.raises(PeriodicNetViewInputError):
        NetViewPolicy(edge_fields=(EdgeSignatureField.RULE_ID, EdgeSignatureField.RULE_ID))


def test_translation_rank_and_index_for_connected_three_periodic_net() -> None:
    topology = periodic_cycle_topology(((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    view = build_periodic_net_view(topology)
    assert view.n_components == 1
    assert view.translation_rank == 3
    assert view.translation_index == 1
    assert view.lifted_component_count == 1
    assert view.is_lift_connected
    assert view.natural_tiling_eligible
    assert set(view.components[0].cycle_gain_generators) == {
        (1, 0, 0),
        (0, 1, 0),
        (0, 0, 1),
    }


def test_translation_index_detects_disconnected_lift_hidden_by_quotient() -> None:
    topology = periodic_cycle_topology(((2, 0, 0), (0, 1, 0), (0, 0, 1)))
    view = build_periodic_net_view(topology)
    assert view.n_components == 1
    assert view.translation_rank == 3
    assert view.translation_index == 2
    assert view.lifted_component_count == 2
    assert not view.is_lift_connected
    assert not view.natural_tiling_eligible


@pytest.mark.parametrize(
    ("shifts", "pbc", "rank", "index"),
    [
        (((0, 0, 0), (1, 0, 0)), (True, False, False), 1, 1),
        (((0, 0, 0), (1, 0, 0), (0, 1, 0)), (True, True, False), 2, 1),
        (((0, 0, 0),), (False, False, False), 0, 1),
    ],
)
def test_partial_periodicity_diagnostics(
    shifts: tuple[tuple[int, int, int], ...],
    pbc: tuple[bool, bool, bool],
    rank: int,
    index: int,
) -> None:
    topology = periodic_cycle_topology(tuple(shift for shift in shifts if shift != (0, 0, 0)), pbc=pbc)
    view = build_periodic_net_view(topology)
    assert view.ambient_periodic_rank == sum(pbc)
    assert view.translation_rank == rank
    assert view.translation_index == index
    assert view.is_lift_connected
    assert not view.natural_tiling_eligible


def test_multiple_quotient_components_are_reported_separately() -> None:
    topology = direct_topology(
        [14, 14, 14, 14, 14, 14],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(0, 2, (1, 0, 0)),
            AtomicEdgeKey(3, 4),
            AtomicEdgeKey(4, 5),
            AtomicEdgeKey(3, 5, (0, 1, 0)),
        ),
    )
    view = build_periodic_net_view(topology)
    assert view.n_components == 2
    assert view.translation_rank is None
    assert view.translation_index is None
    assert view.lifted_component_count is None
    assert [component.translation_rank for component in view.components] == [1, 1]
    assert not view.natural_tiling_eligible


def test_round_trip_requires_exact_source_topology() -> None:
    topology = periodic_cycle_topology(((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    view = build_periodic_net_view(topology, policy=NetViewPolicy.chemically_decorated())
    payload = json.loads(json.dumps(view.to_dict()))
    assert PeriodicNetView.from_dict(payload, topology=topology) == view

    other = periodic_cycle_topology(((1, 0, 0),))
    with pytest.raises(PeriodicNetViewSerializationError):
        PeriodicNetView.from_dict(payload, topology=other)

    payload["digest"] = "0" * 64
    with pytest.raises(PeriodicNetViewSerializationError):
        PeriodicNetView.from_dict(payload, topology=topology)


def test_lookup_rejects_absent_source_records() -> None:
    topology = periodic_cycle_topology(((1, 0, 0),))
    view = build_periodic_net_view(topology)
    assert view.vertex_position(0) == 0
    assert view.edge_position(view.edge_keys[0]) == 0
    with pytest.raises(PeriodicNetViewInputError):
        view.vertex_position(99)


def test_na_lta_is_one_connected_rank_three_index_one_net() -> None:
    topology = FrameworkTopology.from_dict(
        json.loads(
            (Path(__file__).parent / "data" / "na_lta_framework_topology.json").read_text()
        )
    )
    view = build_periodic_net_view(topology)
    assert view.n_vertices == topology.n_vertices
    assert view.n_edges == topology.n_edges
    assert view.n_components == 1
    assert view.translation_rank == 3
    assert view.translation_index == 1
    assert view.natural_tiling_eligible
    assert len(set(view.vertex_signatures)) == 1
    assert len(set(view.edge_signatures)) == 1
