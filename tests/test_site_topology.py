from __future__ import annotations

from collections import Counter
from copy import deepcopy

import pytest

import mdstats.analysis as analysis
from mdstats.analysis import (
    CageInteriorRule,
    FrameworkSemanticCatalog,
    LTA_FRAMEWORK_PROFILE,
    PeriodicSiteKineticNetwork,
    RingSiteRule,
    SiteKineticNetworkResourceError,
    SiteKineticNetworkResources,
    SiteLandscapeRegime,
    SiteStateKind,
    SiteTopologyInputError,
    SiteTopologyInvariantError,
    SiteTopologyResourceError,
    SiteTopologyResources,
    SiteTopologySerializationError,
    SiteTransitionClass,
    SpeciesSiteTopologyCatalog,
    SpeciesSiteTopologyProfile,
    TileTransferRule,
    build_framework_semantic_catalog,
    build_site_kinetic_network,
    build_species_site_topology,
)

from tests._ring_geometry_fixture import lta_reference_ring_geometry_fixture


@pytest.fixture(scope="module")
def sources():
    _topology, _reference, geometry, _collection, _connectivity, ring_geometry = (
        lta_reference_ring_geometry_fixture()
    )
    semantics = build_framework_semantic_catalog(geometry, profile=LTA_FRAMEWORK_PROFILE)
    return geometry, ring_geometry, semantics


def lta_profile(*, eight_regime=SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE):
    if eight_regime is SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE:
        eight = RingSiteRule("alpha_alpha_8r", eight_regime, "8R off-center", radial_offset=1.0, angular_count=4)
    elif eight_regime is SiteLandscapeRegime.PLANE_ANNULAR:
        eight = RingSiteRule("alpha_alpha_8r", eight_regime, "8R annulus", radial_offset=1.0)
    else:
        raise AssertionError
    return SpeciesSiteTopologyProfile(
        "na_lta_geometric_hypotheses",
        "Na",
        "Test-only geometric hypotheses; not energetic certification.",
        (
            RingSiteRule("d4r_alpha_4r", SiteLandscapeRegime.ONE_SIDED, "4R alpha-side", active_tile_label="alpha", normal_offsets=(1.0,)),
            RingSiteRule("d4r_beta_4r", SiteLandscapeRegime.NO_BOUND_STATE, "No 4R beta-side state"),
            RingSiteRule("alpha_beta_6r", SiteLandscapeRegime.PLANE_CENTERED, "6R centered"),
            eight,
        ),
        (CageInteriorRule("alpha", "alpha_interior", "alpha cage interior"),),
        ("test-only",),
    )


@pytest.fixture(scope="module")
def site_catalog(sources):
    geometry, ring_geometry, semantics = sources
    return build_species_site_topology(geometry, ring_geometry, semantics, lta_profile())


def test_lta_explicit_profile_builds_expected_anchors_models_and_states(site_catalog):
    assert len(site_catalog.anchors) == 116
    assert len(site_catalog.ring_models) == 58
    assert len(site_catalog.states) == 66
    assert Counter(model.regime for model in site_catalog.ring_models) == {
        SiteLandscapeRegime.ONE_SIDED: 24,
        SiteLandscapeRegime.NO_BOUND_STATE: 12,
        SiteLandscapeRegime.PLANE_CENTERED: 16,
        SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE: 6,
    }
    assert Counter(state.kind for state in site_catalog.states) == {
        SiteStateKind.RING_SIDE: 24,
        SiteStateKind.RING_CENTER: 16,
        SiteStateKind.RING_OFF_CENTER: 24,
        SiteStateKind.CAGE_INTERIOR: 2,
    }


def test_two_topological_anchors_remain_distinct_and_centered_states_merge_them(site_catalog):
    for model in site_catalog.ring_models:
        a, b = (site_catalog.anchors[index] for index in model.anchor_indices)
        assert a.window_index == b.window_index == model.window_index
        assert a.side_label == "a" and b.side_label == "b"
        if a.resolved and b.resolved:
            assert a.center == pytest.approx(b.center)
            assert a.inward_unit_normal == pytest.approx(tuple(-value for value in b.inward_unit_normal))
        if model.regime is SiteLandscapeRegime.PLANE_CENTERED:
            (state,) = site_catalog.states_for_window(model.window_index)
            assert state.anchor_indices == model.anchor_indices
            assert len(state.exposures) == 2


def test_one_sided_rules_select_the_semantic_tile_not_arbitrary_side_a(site_catalog):
    for model in site_catalog.ring_models:
        if model.regime is not SiteLandscapeRegime.ONE_SIDED:
            continue
        (state,) = site_catalog.states_for_window(model.window_index)
        (anchor_index,) = state.anchor_indices
        anchor = site_catalog.anchors[anchor_index]
        assert anchor.tile_label == "alpha"
        assert state.side_affinity.value == anchor.side_label


def test_discrete_angular_states_are_cyclic_and_annulus_is_not_discretized(sources, site_catalog):
    geometry, ring_geometry, semantics = sources
    network = build_site_kinetic_network(site_catalog, semantics)
    angular = [edge for edge in network.edges if edge.edge_class is SiteTransitionClass.INTRA_RING_ANGULAR]
    assert len(angular) == 48
    assert all(edge.periodic_translation == (0, 0, 0) for edge in angular)

    annular = build_species_site_topology(geometry, ring_geometry, semantics, lta_profile(eight_regime=SiteLandscapeRegime.PLANE_ANNULAR))
    assert Counter(state.kind for state in annular.states)[SiteStateKind.RING_ANNULAR] == 6
    annular_network = build_site_kinetic_network(annular, semantics)
    assert not any(edge.edge_class is SiteTransitionClass.INTRA_RING_ANGULAR for edge in annular_network.edges)


def test_cage_candidates_create_ring_to_cage_paths_but_shared_tiles_do_not_imply_transfer(sources, site_catalog):
    _geometry, _ring_geometry, semantics = sources
    network = build_site_kinetic_network(site_catalog, semantics)
    counts = Counter(edge.edge_class for edge in network.edges)
    assert counts == {
        SiteTransitionClass.INTRA_RING_ANGULAR: 48,
        SiteTransitionClass.RING_TO_CAGE: 176,
    }
    assert SiteTransitionClass.INTRA_TILE_TRANSFER not in counts


def test_intra_tile_transfer_is_explicit_and_preserves_periodic_labels(sources, site_catalog):
    _geometry, _ring_geometry, semantics = sources
    network = build_site_kinetic_network(
        site_catalog,
        semantics,
        transfer_rules=(TileTransferRule("alpha", ("d4r_alpha_4r", "alpha_beta_6r")),),
    )
    transfers = [edge for edge in network.edges if edge.edge_class is SiteTransitionClass.INTRA_TILE_TRANSFER]
    assert transfers
    reverse = {(e.target_state_index, e.source_state_index, tuple(-v for v in e.periodic_translation)) for e in transfers}
    assert all((e.source_state_index, e.target_state_index, e.periodic_translation) in reverse for e in transfers)


def test_bilateral_rules_create_two_nodes_and_translation_labeled_crossings(sources):
    geometry, ring_geometry, semantics = sources
    profile = SpeciesSiteTopologyProfile(
        "na_lta_bilateral_test", "Na", "Bilateral test profile.",
        (
            RingSiteRule("d4r_alpha_4r", SiteLandscapeRegime.BILATERAL_DOUBLE_WELL, "4R bilateral", normal_offsets=(0.8, 1.1)),
            RingSiteRule("d4r_beta_4r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),
            RingSiteRule("alpha_beta_6r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),
            RingSiteRule("alpha_alpha_8r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),
        ),
    )
    topology = build_species_site_topology(geometry, ring_geometry, semantics, profile)
    network = build_site_kinetic_network(topology, semantics)
    crossings = [edge for edge in network.edges if edge.edge_class is SiteTransitionClass.INTRA_RING_CROSSING]
    assert len(crossings) == 48
    for model in topology.ring_models:
        if model.regime is not SiteLandscapeRegime.BILATERAL_DOUBLE_WELL:
            continue
        assert len(model.state_indices) == 2
        edges = [edge for edge in crossings if edge.window_index == model.window_index]
        assert len(edges) == 2
        assert edges[0].periodic_translation == tuple(-v for v in edges[1].periodic_translation)


def test_generic_semantics_are_supported_without_lta_names(sources):
    geometry, ring_geometry, _semantics = sources
    generic = build_framework_semantic_catalog(geometry)
    labels = sorted({interface.generic_label for interface in generic.interfaces})
    profile = SpeciesSiteTopologyProfile(
        "generic_no_bound", "X", "Generic explicit no-bound profile.",
        tuple(RingSiteRule(label, SiteLandscapeRegime.NO_BOUND_STATE, "none") for label in labels),
    )
    topology = build_species_site_topology(geometry, ring_geometry, generic, profile)
    assert not topology.states
    assert all(model.regime is SiteLandscapeRegime.NO_BOUND_STATE for model in topology.ring_models)


def test_profile_coverage_and_resource_preflight_are_strict(sources):
    geometry, ring_geometry, semantics = sources
    incomplete = SpeciesSiteTopologyProfile(
        "incomplete", "Na", "Incomplete.",
        (RingSiteRule("d4r_alpha_4r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),),
    )
    with pytest.raises(SiteTopologyInvariantError, match="coverage mismatch"):
        build_species_site_topology(geometry, ring_geometry, semantics, incomplete)
    with pytest.raises(SiteTopologyResourceError, match="max_anchors"):
        build_species_site_topology(geometry, ring_geometry, semantics, lta_profile(), resources=SiteTopologyResources(max_anchors=1))
    with pytest.raises(SiteTopologyResourceError, match="max_states"):
        build_species_site_topology(geometry, ring_geometry, semantics, lta_profile(), resources=SiteTopologyResources(max_states=1))
    topology = build_species_site_topology(geometry, ring_geometry, semantics, lta_profile())
    with pytest.raises(SiteKineticNetworkResourceError, match="max_edges"):
        build_site_kinetic_network(topology, semantics, resources=SiteKineticNetworkResources(max_edges=1))


def test_serialization_replay_tamper_rejection_and_public_exports(sources, site_catalog):
    geometry, ring_geometry, semantics = sources
    assert SpeciesSiteTopologyCatalog.from_dict(site_catalog.to_dict(), geometry=geometry, ring_geometry=ring_geometry, semantics=semantics) == site_catalog
    network = build_site_kinetic_network(site_catalog, semantics)
    assert PeriodicSiteKineticNetwork.from_dict(network.to_dict(), topology=site_catalog, semantics=semantics) == network
    tampered = deepcopy(site_catalog.to_dict())
    tampered["states"][0]["reference_position"][0] += 0.1
    with pytest.raises(SiteTopologySerializationError):
        SpeciesSiteTopologyCatalog.from_dict(tampered, geometry=geometry, ring_geometry=ring_geometry, semantics=semantics)
    for name in (
        "SpeciesSiteTopologyCatalog", "SpeciesSiteTopologyProfile", "RingSideAnchor",
        "RingSiteRule", "SiteLandscapeRegime", "build_species_site_topology",
        "PeriodicSiteKineticNetwork", "SiteTransitionClass", "TileTransferRule",
        "build_site_kinetic_network",
    ):
        assert hasattr(analysis, name)
        assert name in analysis.__all__

def test_two_variant_angular_cycle_has_one_reversible_pair_per_ring(sources):
    geometry, ring_geometry, semantics = sources
    profile = SpeciesSiteTopologyProfile(
        "two_variant_cycle", "Na", "Two-variant angular-cycle regression.",
        (
            RingSiteRule("d4r_alpha_4r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),
            RingSiteRule("d4r_beta_4r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),
            RingSiteRule("alpha_beta_6r", SiteLandscapeRegime.NO_BOUND_STATE, "none"),
            RingSiteRule("alpha_alpha_8r", SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE, "two variants", radial_offset=1.0, angular_count=2),
        ),
    )
    topology = build_species_site_topology(geometry, ring_geometry, semantics, profile)
    network = build_site_kinetic_network(topology, semantics)
    angular = [edge for edge in network.edges if edge.edge_class is SiteTransitionClass.INTRA_RING_ANGULAR]
    assert len(angular) == 12


def test_unknown_cage_label_and_incompatible_rule_parameters_are_rejected(sources):
    geometry, ring_geometry, semantics = sources
    profile = SpeciesSiteTopologyProfile(
        "unknown_cage", "Na", "Unknown cage label regression.",
        lta_profile().ring_rules,
        (CageInteriorRule("not_a_tile", "interior", "interior"),),
    )
    with pytest.raises(SiteTopologyInvariantError, match="unknown tile labels"):
        build_species_site_topology(geometry, ring_geometry, semantics, profile)
    with pytest.raises(SiteTopologyInputError):
        RingSiteRule(
            "alpha_beta_6r", SiteLandscapeRegime.PLANE_CENTERED, "center",
            angular_phase=0.5,
        )
