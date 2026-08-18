"""Focused tests for role-aware periodic framework projection."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    ConnectivityScope,
    DistanceConnectivity,
    ExplicitConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkComplexityError,
    FrameworkEdgeKey,
    FrameworkEdgePath,
    FrameworkMapping,
    FrameworkMappingError,
    FrameworkPathRule,
    FrameworkProjectionError,
    FrameworkProjectionOptions,
    FrameworkTopology,
    FrameworkValidationError,
    FrameworkValidationRules,
    PairCutoffRegistry,
    build_framework_topology,
    compute_atomic_connectivity,
    read_structure,
    resolve_framework_roles,
    validate_framework_topology,
)
from mdstats.analysis.atomic_connectivity import (
    AtomicEdgeKey,
    build_atomic_connectivity_state,
)


def make_collection(
    atomic_numbers: list[int] | np.ndarray,
    *,
    positions: np.ndarray | None = None,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> AtomisticFrameCollection:
    numbers = np.asarray(atomic_numbers, dtype=np.int32)
    n_atoms = numbers.size
    xyz = (
        np.arange(n_atoms * 3, dtype=float).reshape(n_atoms, 3) * 0.1
        if positions is None
        else np.asarray(positions, dtype=float)
    )
    cell = np.eye(3) * 10.0
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=numbers,
        masses=np.ones(n_atoms),
        pbc=np.asarray(pbc, dtype=bool),
        steps=None,
        times=None,
        cells=cell[None, ...],
        origins=np.zeros((1, 3)),
        fractional_positions=(xyz @ np.linalg.inv(cell))[None, ...],
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


def explicit_state(
    atomic_numbers: list[int],
    edges: tuple[AtomicEdgeKey, ...],
    *,
    pbc: tuple[bool, bool, bool] = (True, True, True),
):
    collection = make_collection(atomic_numbers, pbc=pbc)
    state = build_atomic_connectivity_state(
        collection,
        ExplicitConnectivity(uniform_edges=edges),
        frame_index=0,
    )
    return collection, state


def tot_mapping(*, sodium_role: FrameworkAtomRole | None = None) -> FrameworkMapping:
    roles: dict[str, FrameworkAtomRole] = {
        "Si": FrameworkAtomRole.VERTEX,
        "Al": FrameworkAtomRole.VERTEX,
        "O": FrameworkAtomRole.LINKER,
    }
    if sodium_role is not None:
        roles["Na"] = sodium_role
    return FrameworkMapping.from_symbol_roles(
        roles,
        path_rules=(
            FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),
        ),
        name="test T-O-T mapping",
    )


def test_simple_vertex_linker_vertex_and_round_trip() -> None:
    _, state = explicit_state(
        [14, 8, 13],
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)),
    )
    topology = build_framework_topology(state, tot_mapping())
    assert topology.n_vertices == 2
    assert topology.n_edges == 1
    np.testing.assert_array_equal(topology.degree, [1, 1])
    edge = topology.edges[0]
    assert edge.atomic_path_indices == (0, 1, 2)
    assert edge.key.internal_linker_indices == (1,)
    assert edge.internal_linker_atomic_numbers == (8,)
    assert edge.edge_kind == "oxygen_bridge"
    assert FrameworkTopology.from_dict(topology.to_dict()) == topology


def test_direct_rule_is_explicit() -> None:
    _, state = explicit_state([14, 13], (AtomicEdgeKey(0, 1),))
    no_direct = build_framework_topology(
        state,
        FrameworkMapping.from_symbol_roles(
            {"Si": "vertex", "Al": "vertex"}, path_rules=()
        ),
    )
    assert no_direct.n_edges == 0
    direct = build_framework_topology(
        state,
        FrameworkMapping.from_symbol_roles(
            {"Si": "vertex", "Al": "vertex"},
            path_rules=(FrameworkPathRule("direct", (), edge_kind="direct"),),
        ),
    )
    assert direct.n_edges == 1
    assert direct.edges[0].atomic_path_indices == (0, 1)


def test_symbol_constructor_override_precedence_and_unmapped_error() -> None:
    _, state = explicit_state([14, 8, 11], (AtomicEdgeKey(0, 1),))
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "O": "linker", "Na": "spectator"},
        atom_role_overrides={1: "excluded"},
        path_rules=(),
    )
    resolved = resolve_framework_roles(state, mapping)
    assert resolved.roles == (
        FrameworkAtomRole.VERTEX,
        FrameworkAtomRole.EXCLUDED,
        FrameworkAtomRole.SPECTATOR,
    )
    numeric = FrameworkMapping(
        species_roles={14: FrameworkAtomRole.VERTEX, 8: FrameworkAtomRole.LINKER},
        path_rules=(),
        unmapped_role=FrameworkAtomRole.SPECTATOR,
    )
    assert (
        resolve_framework_roles(state, numeric).roles[2] is FrameworkAtomRole.SPECTATOR
    )
    with pytest.raises(FrameworkMappingError, match="no framework role"):
        resolve_framework_roles(
            state,
            FrameworkMapping(species_roles={14: FrameworkAtomRole.VERTEX}),
        )


def test_overlapping_rules_are_rejected_including_reversal() -> None:
    first = FrameworkPathRule.from_symbols("OS", ("O", "S"))
    reversed_rule = FrameworkPathRule.from_symbols("SO", ("S", "O"))
    with pytest.raises(FrameworkMappingError, match="overlap"):
        FrameworkMapping.from_symbol_roles(
            {"Si": "vertex", "O": "linker", "S": "linker"},
            path_rules=(first, reversed_rule),
        )


def test_asymmetric_rule_couples_endpoint_and_linker_orientation() -> None:
    rule = FrameworkPathRule.from_symbols(
        "Si-O-S-Al",
        ("O", "S"),
        endpoint_symbols=("Si", "Al"),
        edge_kind="asymmetric_bridge",
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker", "S": "linker"},
        path_rules=(rule,),
    )

    _, forward_state = explicit_state(
        [14, 8, 16, 13],
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(2, 3)),
    )
    forward = build_framework_topology(forward_state, mapping)
    assert forward.n_edges == 1
    assert forward.edges[0].internal_linker_atomic_numbers == (8, 16)

    _, reverse_state = explicit_state(
        [13, 16, 8, 14],
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(2, 3)),
    )
    reverse = build_framework_topology(reverse_state, mapping)
    assert reverse.n_edges == 1
    assert reverse.edges[0].internal_linker_atomic_numbers == (16, 8)

    _, wrong_state = explicit_state(
        [14, 16, 8, 13],
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(2, 3)),
    )
    wrong = build_framework_topology(wrong_state, mapping)
    assert wrong.n_edges == 0


def test_whole_path_reverse_declarations_have_identical_mapping_identity() -> None:
    forward = FrameworkPathRule.from_symbols(
        "asymmetric", ("O", "S"), endpoint_symbols=("Si", "Al")
    )
    reverse = FrameworkPathRule.from_symbols(
        "asymmetric", ("S", "O"), endpoint_symbols=("Al", "Si")
    )
    assert forward == reverse
    assert forward.canonical_signature == reverse.canonical_signature

    roles = {"Si": "vertex", "Al": "vertex", "O": "linker", "S": "linker"}
    assert (
        FrameworkMapping.from_symbol_roles(roles, path_rules=(forward,)).digest
        == FrameworkMapping.from_symbol_roles(roles, path_rules=(reverse,)).digest
    )


def test_swapped_asymmetric_patterns_are_distinct_and_may_coexist() -> None:
    os_rule = FrameworkPathRule.from_symbols(
        "Si-O-S-Al", ("O", "S"), endpoint_symbols=("Si", "Al")
    )
    so_rule = FrameworkPathRule.from_symbols(
        "Si-S-O-Al", ("S", "O"), endpoint_symbols=("Si", "Al")
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker", "S": "linker"},
        path_rules=(os_rule, so_rule),
    )
    _, state = explicit_state(
        [14, 8, 16, 16, 8, 13],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 5),
            AtomicEdgeKey(0, 3),
            AtomicEdgeKey(3, 4),
            AtomicEdgeKey(4, 5),
        ),
    )
    topology = build_framework_topology(state, mapping)
    assert topology.n_edges == 2
    assert {edge.key.rule_id for edge in topology.edges} == {
        "Si-O-S-Al",
        "Si-S-O-Al",
    }
    assert {edge.internal_linker_atomic_numbers for edge in topology.edges} == {
        (8, 16),
        (16, 8),
    }


def test_oriented_edge_view_reverses_complete_path_and_periodic_data() -> None:
    edge = FrameworkEdgePath(
        key=FrameworkEdgeKey(
            vertex_i=0,
            vertex_j=3,
            image_shift=(1, 0, 0),
            internal_linker_indices=(1, 2),
            internal_linker_image_offsets=((0, 0, 0), (1, 0, 0)),
            rule_id="Si-O-S-Al",
        ),
        atomic_path_indices=(0, 1, 2, 3),
        atomic_edge_image_shifts=((0, 0, 0), (1, 0, 0), (0, 0, 0)),
        internal_linker_atomic_numbers=(8, 16),
        raw_image_shift=(1, 0, 0),
        edge_kind="asymmetric_bridge",
    )
    forward = edge.oriented(1)
    reverse = edge.oriented(-1)
    assert forward.atomic_path_indices == (0, 1, 2, 3)
    assert reverse.atomic_path_indices == (3, 2, 1, 0)
    assert reverse.internal_linker_indices == (2, 1)
    assert reverse.internal_linker_atomic_numbers == (16, 8)
    assert reverse.atomic_edge_image_shifts == (
        (0, 0, 0),
        (-1, 0, 0),
        (0, 0, 0),
    )
    assert reverse.internal_linker_image_offsets == ((0, 0, 0), (-1, 0, 0))
    assert reverse.image_shift == (-1, 0, 0)
    assert reverse.raw_image_shift == (-1, 0, 0)
    assert edge.oriented_from(3) == reverse
    with pytest.raises(FrameworkProjectionError, match="not an endpoint"):
        edge.oriented_from(99)


def test_framework_rule_v2_serialization_preserves_coupled_signature() -> None:
    rule = FrameworkPathRule.from_symbols(
        "Si-O-S-Al", ("O", "S"), endpoint_symbols=("Si", "Al")
    )
    payload = rule.to_dict()
    assert "endpoint_atomic_numbers" in payload
    assert "endpoint_atomic_number_pairs" not in payload
    assert FrameworkPathRule.from_dict(payload) == rule


def test_version1_endpoint_pair_rule_payload_is_rejected() -> None:
    with pytest.raises(FrameworkMappingError, match="cannot be migrated"):
        FrameworkPathRule.from_dict(
            {
                "rule_id": "legacy",
                "linker_atomic_numbers": [8, 16],
                "endpoint_atomic_number_pairs": [[13, 14]],
                "edge_kind": "framework",
            }
        )


def test_spectator_and_excluded_atoms_block_paths() -> None:
    _, state = explicit_state(
        [14, 8, 11, 8, 13],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(3, 4),
        ),
    )
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "Al": "vertex", "O": "linker", "Na": "spectator"},
        path_rules=(FrameworkPathRule.from_symbols("O-O", ("O", "O")),),
    )
    spectator = build_framework_topology(state, mapping)
    assert spectator.n_edges == 0
    assert spectator.projection_report.ignored_atomic_edge_count == 2
    excluded = build_framework_topology(
        state,
        FrameworkMapping.from_symbol_roles(
            {"Si": "vertex", "Al": "vertex", "O": "linker", "Na": "excluded"},
            path_rules=(FrameworkPathRule.from_symbols("O-O", ("O", "O")),),
        ),
    )
    assert excluded.n_edges == 0


def test_intermediate_vertex_terminates_longer_path() -> None:
    _, state = explicit_state(
        [14, 8, 13, 8, 14],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(1, 2),
            AtomicEdgeKey(2, 3),
            AtomicEdgeKey(3, 4),
        ),
    )
    topology = build_framework_topology(state, tot_mapping())
    assert {(e.key.vertex_i, e.key.vertex_j) for e in topology.edges} == {
        (0, 2),
        (2, 4),
    }


def test_parallel_paths_survive_and_branching_is_diagnostic() -> None:
    _, state = explicit_state(
        [14, 8, 8, 13],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(1, 3),
            AtomicEdgeKey(2, 3),
        ),
    )
    topology = build_framework_topology(state, tot_mapping())
    assert topology.n_edges == 2
    assert topology.projection_report.parallel_vertex_pair_count == 1
    assert {edge.key.internal_linker_indices for edge in topology.edges} == {(1,), (2,)}

    _, branch_state = explicit_state(
        [14, 8, 13, 14],
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2), AtomicEdgeKey(1, 3)),
    )
    branch = build_framework_topology(branch_state, tot_mapping())
    np.testing.assert_array_equal(
        branch.projection_report.branching_linker_atom_indices, [1]
    )
    assert branch.n_edges == 3


def test_dangling_and_unused_linker_diagnostics_and_isolated_vertex() -> None:
    _, state = explicit_state(
        [14, 8, 8, 13],
        (AtomicEdgeKey(0, 1),),
    )
    topology = build_framework_topology(state, tot_mapping())
    assert topology.n_vertices == 2
    assert topology.n_edges == 0
    assert topology.n_components == 2
    np.testing.assert_array_equal(
        topology.projection_report.unused_linker_atom_indices, [1, 2]
    )
    np.testing.assert_array_equal(
        topology.projection_report.dangling_linker_atom_indices, [1, 2]
    )


def test_periodic_winding_is_composed_and_reverse_discovery_deduplicated() -> None:
    # Two projected paths form a quotient-graph cycle; one retains winding after
    # deterministic projected gauge normalization.
    _, state = explicit_state(
        [14, 8, 8, 13],
        (
            AtomicEdgeKey(0, 1, (0, 0, 0)),
            AtomicEdgeKey(0, 2, (1, 0, 0)),
            AtomicEdgeKey(1, 3, (0, 0, 0)),
            AtomicEdgeKey(2, 3, (0, 0, 0)),
        ),
    )
    topology = build_framework_topology(state, tot_mapping())
    assert topology.n_edges == 2
    assert any(edge.raw_image_shift != (0, 0, 0) for edge in topology.edges)
    assert topology.projection_report.duplicate_path_count >= 2
    assert sum(edge.key.image_shift != (0, 0, 0) for edge in topology.edges) == 1


def test_projected_self_image_edge_and_zero_winding_self_return_rejection() -> None:
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("O-O", ("O", "O")),),
    )
    _, winding_state = explicit_state(
        [14, 8, 8],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(0, 2, (1, 0, 0)),
            AtomicEdgeKey(1, 2),
        ),
    )
    winding = build_framework_topology(winding_state, mapping)
    assert winding.n_edges == 1
    assert winding.edges[0].key.vertex_i == winding.edges[0].key.vertex_j == 0
    assert winding.edges[0].key.image_shift != (0, 0, 0)
    assert winding.degree_for_atom(0) == 2

    _, zero_state = explicit_state(
        [14, 8, 8],
        (AtomicEdgeKey(0, 1), AtomicEdgeKey(0, 2), AtomicEdgeKey(1, 2)),
    )
    zero = build_framework_topology(zero_state, mapping)
    assert zero.n_edges == 0


def test_complexity_limits_fail_without_partial_results() -> None:
    _, state = explicit_state(
        [14, 8, 8, 13],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(1, 3),
            AtomicEdgeKey(2, 3),
        ),
    )
    with pytest.raises(FrameworkComplexityError, match="candidate-path"):
        build_framework_topology(
            state,
            tot_mapping(),
            options=FrameworkProjectionOptions(max_candidate_paths=1),
        )
    with pytest.raises(FrameworkComplexityError, match="edge limit"):
        build_framework_topology(
            state,
            tot_mapping(),
            options=FrameworkProjectionOptions(max_projected_edges=1),
        )
    long_rule = FrameworkMapping.from_symbol_roles(
        {"Si": "vertex", "O": "linker"},
        path_rules=(FrameworkPathRule.from_symbols("OO", ("O", "O")),),
    )
    with pytest.raises(FrameworkComplexityError, match="linker length"):
        build_framework_topology(
            state,
            long_rule,
            options=FrameworkProjectionOptions(max_linker_atoms=1),
        )


def test_validation_reports_without_modifying_topology() -> None:
    _, state = explicit_state([14, 8, 13], (AtomicEdgeKey(0, 1), AtomicEdgeKey(1, 2)))
    topology = build_framework_topology(state, tot_mapping())
    digest_before = topology.digest
    good = FrameworkValidationRules(
        allowed_vertex_degrees={14: frozenset({1}), 13: frozenset({1})},
        allowed_linker_degrees={8: frozenset({2})},
        expected_vertex_count=2,
        expected_edge_count=1,
        require_single_component=True,
        require_all_linkers_used=True,
        allowed_edge_kinds=frozenset({"oxygen_bridge"}),
    )
    assert validate_framework_topology(topology, good).passed
    bad = FrameworkValidationRules(
        allowed_vertex_degrees={14: frozenset({4})},
        expected_edge_count=2,
        require_all_linkers_used=True,
    )
    report = validate_framework_topology(topology, bad)
    assert not report.passed
    assert {issue.code for issue in report.issues} == {
        "invalid_vertex_degree",
        "unexpected_edge_count",
    }
    with pytest.raises(FrameworkValidationError):
        report.raise_for_errors()
    assert topology.digest == digest_before


def test_mapping_topology_serialization_and_networkx_multigraph() -> None:
    mapping = tot_mapping()
    assert FrameworkMapping.from_dict(mapping.to_dict()) == mapping
    _, state = explicit_state(
        [14, 8, 8, 13],
        (
            AtomicEdgeKey(0, 1),
            AtomicEdgeKey(0, 2),
            AtomicEdgeKey(1, 3),
            AtomicEdgeKey(2, 3),
        ),
    )
    topology = build_framework_topology(state, mapping)
    restored = FrameworkTopology.from_dict(topology.to_dict())
    assert restored == topology
    graph = topology.to_networkx()
    assert graph.is_multigraph()
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 2


def test_relaxed_na_lta_projection_and_spectator_contact_invariance() -> None:
    structure = Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR"
    collection = read_structure(structure, format="vasp")
    mapping = tot_mapping(sodium_role=FrameworkAtomRole.SPECTATOR)
    validation = FrameworkValidationRules(
        allowed_vertex_degrees={14: frozenset({4}), 13: frozenset({4})},
        allowed_linker_degrees={8: frozenset({2})},
        expected_vertex_count=48,
        expected_edge_count=96,
        require_single_component=True,
        require_all_linkers_used=True,
        allow_parallel_edges=False,
        allow_self_image_edges=False,
        allowed_edge_kinds=frozenset({"oxygen_bridge"}),
    )
    framework_result = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {("Si", "O"): 2.0, ("Al", "O"): 2.0}
            ),
            scope=ConnectivityScope.from_selection(
                included_atom_indices=tuple(range(144))
            ),
        ),
    )
    framework = build_framework_topology(
        framework_result.states[0], mapping, validation_rules=validation
    )
    assert framework.n_vertices == 48
    assert framework.n_edges == 96
    np.testing.assert_array_equal(framework.degree, np.full(48, 4))
    assert framework.n_components == 1
    assert framework.validation is not None and framework.validation.passed
    np.testing.assert_array_equal(
        framework.projection_report.linker_framework_degree, np.full(96, 2)
    )

    broad_result = compute_atomic_connectivity(
        collection,
        DistanceConnectivity(
            cutoffs=PairCutoffRegistry.from_mapping(
                {
                    ("Si", "O"): 2.0,
                    ("Al", "O"): 2.0,
                    ("Na", "O"): 3.15,
                }
            ),
        ),
    )
    broad = build_framework_topology(broad_result.states[0], mapping)
    assert broad.n_vertices == 48
    assert broad.n_edges == 96
    assert broad.graph_digest == framework.graph_digest
    assert broad.digest == framework.digest
    assert broad.source_connectivity_digest != framework.source_connectivity_digest
    assert broad.projection_report.ignored_atomic_edge_count > 0
