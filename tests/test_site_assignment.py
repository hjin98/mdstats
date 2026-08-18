from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

import mdstats
import mdstats.analysis as analysis
from mdstats.analysis import (
    CageInteriorRule,
    LTA_FRAMEWORK_PROFILE,
    RingSiteRule,
    SiteAssignmentInputError,
    SiteAssignmentProfile,
    SiteAssignmentResourceError,
    SiteAssignmentResources,
    SiteAssignmentResult,
    SiteAssignmentRule,
    SiteAssignmentSerializationError,
    SiteAssignmentStatus,
    SiteLandscapeRegime,
    SiteStateKind,
    SpeciesSiteTopologyProfile,
    assign_trajectory_sites,
    build_framework_semantic_catalog,
    build_site_kinetic_network,
    build_species_site_topology,
)
from tests.test_ring_geometry_frames import _build
from tests._ring_geometry_fixture import lta_reference_ring_geometry_fixture


def _site_profile(*, annular: bool = False):
    eight = (
        RingSiteRule("alpha_alpha_8r", SiteLandscapeRegime.PLANE_ANNULAR, "8R annulus", radial_offset=1.0)
        if annular
        else RingSiteRule("alpha_alpha_8r", SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE, "8R angular", radial_offset=1.0, angular_count=4)
    )
    return SpeciesSiteTopologyProfile(
        "na_lta_assignment_fixture" + ("_annular" if annular else ""),
        "Na",
        "Test-only geometric hypotheses.",
        (
            RingSiteRule("d4r_alpha_4r", SiteLandscapeRegime.ONE_SIDED, "4R alpha", active_tile_label="alpha", normal_offsets=(1.0,)),
            RingSiteRule("d4r_beta_4r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),
            RingSiteRule("alpha_beta_6r", SiteLandscapeRegime.PLANE_CENTERED, "6R center"),
            eight,
        ),
        (CageInteriorRule("alpha", "alpha_interior", "alpha interior"),),
        ("test-only",),
    )


def _assignment_profile(topology, *, width=0.12, transition=1.8):
    kinds = sorted({state.kind for state in topology.states}, key=lambda value: value.value)
    return SiteAssignmentProfile(
        "na_lta_assignment_rules",
        topology.profile.profile_id,
        "Na",
        "Explicit test basin widths.",
        tuple(
            SiteAssignmentRule(
                f"rule_{kind.value}",
                width,
                width if kind is not SiteStateKind.CAGE_INTERIOR else 0.25,
                transition,
                state_kind=kind,
            )
            for kind in kinds
        ),
        ("test-only",),
    )


def _state_position(state, topology, reference):
    if state.kind is SiteStateKind.CAGE_INTERIOR:
        return np.asarray(state.reference_position)
    ring = reference.rings[state.window_index]
    anchor = topology.anchors[state.anchor_indices[0]]
    frame = next(item for item in ring.side_frames if item.side == anchor.side)
    center = np.asarray(frame.center)
    normal = np.asarray(frame.inward_unit_normal)
    axis_u = np.asarray(frame.axis_u)
    axis_v = np.asarray(frame.axis_v)
    z, rho, theta = state.local_coordinates
    return center + z * normal + rho * (np.cos(theta) * axis_u + np.sin(theta) * axis_v)


def _set_cartesian(fractional, frame, atom, point, cell, *, image=(0, 0, 0)):
    fractional[frame, atom] = np.asarray(point) @ np.linalg.inv(cell) + np.asarray(image)


@pytest.fixture(scope="module")
def prepared():
    _topology_ref, reference_data, geometry, single, base_connectivity, reference = (
        lta_reference_ring_geometry_fixture()
    )
    sources = SimpleNamespace(
        single=single,
        scope=base_connectivity.definition.scope,
        base_edges=base_connectivity.states[0].edge_keys,
        reference=reference_data,
        geometry=geometry,
    )
    semantics = build_framework_semantic_catalog(sources.geometry, profile=LTA_FRAMEWORK_PROFILE)
    topology = build_species_site_topology(sources.geometry, reference, semantics, _site_profile())
    network = build_site_kinetic_network(topology, semantics)
    na_atoms = np.flatnonzero(sources.single.atomic_numbers == 11)
    atom = int(na_atoms[0])
    angular_edge = next(edge for edge in network.edges if edge.edge_class.value == "intra_ring_angular")
    source = topology.states[angular_edge.source_state_index]
    target = topology.states[angular_edge.target_state_index]
    fractional = np.repeat(sources.single.fractional_positions, 4, axis=0)
    cell = sources.single.cells[0]
    _set_cartesian(fractional, 0, atom, _state_position(source, topology, reference), cell)
    _set_cartesian(fractional, 1, atom, _state_position(target, topology, reference), cell)
    # One transition-shell point displaced from the target along its local u axis.
    ring = reference.rings[target.window_index]
    anchor = topology.anchors[target.anchor_indices[0]]
    frame = next(item for item in ring.side_frames if item.side == anchor.side)
    _set_cartesian(
        fractional, 2, atom,
        _state_position(target, topology, reference) + 0.16 * np.asarray(frame.axis_u),
        cell,
    )
    # Preserve the original Na position as a deliberately unassigned sample under narrow rules.
    collection, connectivity, catalog, frame_tiling, reference2, frame_rings = _build(sources, fractional)
    # Stage 11C1 source binding includes the concrete collection. Rebuild the
    # Stage 11E1 topology against the final trajectory source, while retaining
    # the geometrically identical candidate positions used above.
    topology2 = build_species_site_topology(sources.geometry, reference2, semantics, _site_profile())
    network2 = build_site_kinetic_network(topology2, semantics)
    angular_edge2 = next(edge for edge in network2.edges if edge.edge_class.value == "intra_ring_angular")
    source2 = topology2.states[angular_edge2.source_state_index]
    target2 = topology2.states[angular_edge2.target_state_index]
    return sources, collection, connectivity, catalog, frame_tiling, frame_rings, reference2, semantics, topology2, network2, atom, source2, target2, angular_edge2


def _assign(prepared, *, profile=None, topology=None, network=None, atom_indices=None, resources=None):
    (_sources, collection, _conn, _cat, frame_tiling, frame_rings, _ref, _sem, default_topology, default_network, atom, *_rest) = prepared
    active_topology = default_topology if topology is None else topology
    active_network = default_network if network is None else network
    return assign_trajectory_sites(
        collection,
        frame_tiling,
        frame_rings,
        active_topology,
        active_network,
        _assignment_profile(active_topology) if profile is None else profile,
        atom_indices=[atom] if atom_indices is None else atom_indices,
        resources=resources,
    )


def test_unique_core_assignments_preserve_state_identity_and_periodic_image(prepared):
    result = _assign(prepared)
    *_, source, target, _edge = prepared[-3:]
    row = result.assignments[0]
    assert row[0].status is SiteAssignmentStatus.ASSIGNED
    assert row[0].state_index == source.state_index
    assert row[1].state_index == target.state_index
    assert row[0].site_image_shift == (0, 0, 0)
    assert np.linalg.norm(row[0].relative_cartesian) < 1.0e-9


def test_transition_shell_and_unassigned_space_are_distinct(prepared):
    result = _assign(prepared)
    row = result.assignments[0]
    assert row[2].status is SiteAssignmentStatus.TRANSITION_REGION
    assert row[2].diagnostics and not row[2].diagnostics[0].core
    assert row[3].status is SiteAssignmentStatus.UNASSIGNED


def test_overlapping_core_basins_are_ambiguous_without_nearest_fallback(prepared):
    topology = prepared[8]
    broad = _assignment_profile(topology, width=20.0, transition=1.1)
    result = _assign(prepared, profile=broad)
    assignment = result.assignments[0][0]
    assert assignment.status is SiteAssignmentStatus.AMBIGUOUS
    assert assignment.state_index is None
    assert sum(item.core for item in assignment.diagnostics) >= 2
    assert result.metadata["nearest_site_fallback"] is False


def test_periodic_site_image_shift_is_retained(prepared):
    sources, _collection, *_ = prepared
    topology = prepared[8]
    state = prepared[11]
    atom = prepared[10]
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    point = _state_position(state, topology, prepared[6])
    _set_cartesian(fractional, 0, atom, point, sources.single.cells[0])
    _set_cartesian(fractional, 1, atom, point, sources.single.cells[0], image=(1, 0, 0))
    collection, _conn, _cat, tiling, reference, rings = _build(sources, fractional)
    semantics = prepared[7]
    topo = build_species_site_topology(sources.geometry, reference, semantics, _site_profile())
    network = build_site_kinetic_network(topo, semantics)
    result = assign_trajectory_sites(collection, tiling, rings, topo, network, _assignment_profile(topo), atom_indices=[atom])
    assert result.assignments[0][0].site_image_shift == (0, 0, 0)
    assert result.assignments[0][1].site_image_shift == (1, 0, 0)
    event = result.ion_statistics[0].observed_transitions[0]
    assert event.source_state_index == event.target_state_index
    assert event.observed_translation == (1, 0, 0)
    assert not event.on_network


def test_observed_structural_transition_matches_state_ids_and_translation(prepared):
    result = _assign(prepared)
    edge = prepared[-1]
    event = result.ion_statistics[0].observed_transitions[0]
    assert (event.source_state_index, event.target_state_index) == (edge.source_state_index, edge.target_state_index)
    assert event.observed_translation == edge.periodic_translation
    assert edge.edge_index in event.matching_edge_indices
    assert event.on_network


def test_auxiliary_outcomes_are_mapped_to_dense_temporal_statistics(prepared):
    result = _assign(prepared)
    stats = result.ion_statistics[0]
    assert stats.temporal_statistics.n_states == len(prepared[8].states) + 4
    assert stats.accepted_frame_count == 2
    assert int(np.sum(stats.physical_frame_counts)) == 2
    assert stats.temporal_statistics.n_frames == 4
    assert stats.temporal_statistics.frame_to_state_id[2] >= len(prepared[8].states)


def test_annular_assignment_retains_continuous_angle(prepared):
    sources = prepared[0]
    semantics = prepared[7]
    reference = prepared[6]
    annular_topology = build_species_site_topology(sources.geometry, reference, semantics, _site_profile(annular=True))
    annular_network = build_site_kinetic_network(annular_topology, semantics)
    state = next(item for item in annular_topology.states if item.kind is SiteStateKind.RING_ANNULAR)
    atom = prepared[10]
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    point = _state_position(state, annular_topology, reference)
    _set_cartesian(fractional, 0, atom, point, sources.single.cells[0])
    _set_cartesian(fractional, 1, atom, point, sources.single.cells[0])
    collection, _conn, _cat, tiling, reference2, rings = _build(sources, fractional)
    annular_topology2 = build_species_site_topology(sources.geometry, reference2, semantics, _site_profile(annular=True))
    annular_network2 = build_site_kinetic_network(annular_topology2, semantics)
    result = assign_trajectory_sites(
        collection, tiling, rings, annular_topology2, annular_network2,
        _assignment_profile(annular_topology2), atom_indices=[atom],
    )
    assignment = result.assignments[0][0]
    assert assignment.status is SiteAssignmentStatus.ANNULAR_ASSIGNED
    assert assignment.annular_angle == pytest.approx(0.0, abs=2.0e-9)


def test_upstream_unresolved_frame_yields_frame_unresolved(prepared):
    sources = prepared[0]
    atom = prepared[10]
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    frame_edges = {0: sources.base_edges, 1: tuple(sources.base_edges[1:])}
    collection, _conn, _cat, tiling, reference, rings = _build(sources, fractional, frame_edges=frame_edges)
    semantics = build_framework_semantic_catalog(sources.geometry, profile=LTA_FRAMEWORK_PROFILE)
    topology = build_species_site_topology(sources.geometry, reference, semantics, _site_profile())
    network = build_site_kinetic_network(topology, semantics)
    result = assign_trajectory_sites(collection, tiling, rings, topology, network, _assignment_profile(topology), atom_indices=[atom])
    assert result.assignments[0][1].status is SiteAssignmentStatus.FRAME_UNRESOLVED
    assert result.assignments[0][1].available_state_count == 0


def test_profile_coverage_species_and_resources_are_strict(prepared):
    topology = prepared[8]
    incomplete = SiteAssignmentProfile(
        "incomplete", topology.profile.profile_id, "Na", "Incomplete.",
        (SiteAssignmentRule("only_cage", 0.1, 0.1, state_kind=SiteStateKind.CAGE_INTERIOR),),
    )
    with pytest.raises(analysis.SiteAssignmentInvariantError, match="matched 0"):
        _assign(prepared, profile=incomplete)
    with pytest.raises(SiteAssignmentInputError, match="assignment-profile species"):
        _assign(prepared, atom_indices=[0])
    with pytest.raises(SiteAssignmentResourceError, match="candidate evaluations"):
        _assign(prepared, resources=SiteAssignmentResources(max_candidate_evaluations=1))


def test_result_is_deeply_immutable_and_publicly_exported(prepared):
    result = _assign(prepared)
    with pytest.raises(ValueError):
        result.atom_indices[0] = 0
    with pytest.raises(ValueError):
        result.ion_statistics[0].physical_frame_counts[0] = 9
    with pytest.raises(TypeError):
        result.metadata["x"] = 1
    assert analysis.assign_trajectory_sites is assign_trajectory_sites
    assert mdstats.assign_trajectory_sites is assign_trajectory_sites
    assert "SiteAssignmentResult" in analysis.__all__ and "SiteAssignmentResult" in mdstats.__all__


def test_canonical_source_replay_and_tamper_rejection(prepared):
    result = _assign(prepared)
    collection, tiling, rings, topology, network = prepared[1], prepared[4], prepared[5], prepared[8], prepared[9]
    rebuilt = SiteAssignmentResult.from_dict(
        result.to_dict(), collection=collection, frame_tiling_geometry=tiling,
        frame_ring_geometry=rings, site_topology=topology, site_network=network,
    )
    assert rebuilt == result
    payload = deepcopy(result.to_dict())
    payload["assignments"][0][0]["state_index"] = 999
    with pytest.raises(SiteAssignmentSerializationError):
        SiteAssignmentResult.from_dict(
            payload, collection=collection, frame_tiling_geometry=tiling,
            frame_ring_geometry=rings, site_topology=topology, site_network=network,
        )
