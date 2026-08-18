from __future__ import annotations

from collections import Counter
from copy import deepcopy

import pytest

import mdstats.analysis as analysis
from mdstats.analysis import (
    FrameworkSemanticCatalog,
    FrameworkSemanticProfile,
    FrameworkSemanticsInputError,
    FrameworkSemanticsInvariantError,
    FrameworkSemanticsResourceError,
    FrameworkSemanticsResources,
    FrameworkSemanticsSerializationError,
    LTA_FRAMEWORK_PROFILE,
    RingInterfaceRule,
    RingInterfaceSignature,
    TileFaceSignature,
    TileSemanticRule,
    build_framework_semantic_catalog,
    build_tiling_geometry_catalog,
)

from tests._lta_tiling_fixture import lta_reference_geometry
from tests.test_periodic_cell_complex import _simple_cubic_fixture


@pytest.fixture(scope="module")
def lta_geometry():
    return lta_reference_geometry()[2]


@pytest.fixture(scope="module")
def lta_semantics(lta_geometry):
    return build_framework_semantic_catalog(
        lta_geometry,
        profile=LTA_FRAMEWORK_PROFILE,
    )


def test_lta_tile_semantics_follow_independently_derived_face_signatures(lta_semantics):
    assert Counter(tile.face_signature.symbol for tile in lta_semantics.tiles) == {
        "4^6": 6,
        "4^6.6^8": 2,
        "4^12.6^8.8^6": 2,
    }
    assert Counter(tile.semantic_label for tile in lta_semantics.tiles) == {
        "d4r": 6,
        "beta": 2,
        "alpha": 2,
    }
    assert Counter(tile.role for tile in lta_semantics.tiles) == {
        "structural_unit": 6,
        "cage": 4,
    }
    assert lta_semantics.validation is not None
    assert lta_semantics.validation.matched


def test_lta_ring_interface_families_are_classified_from_ring_order_and_adjacency(
    lta_semantics,
):
    assert Counter(interface.family_label for interface in lta_semantics.interfaces) == {
        "d4r_alpha_4r": 24,
        "d4r_beta_4r": 12,
        "alpha_beta_6r": 16,
        "alpha_alpha_8r": 6,
    }
    assert Counter(interface.role for interface in lta_semantics.interfaces) == {
        "exposed_4r": 24,
        "internal_4r": 12,
        "cage_interface": 16,
        "window": 6,
    }
    for interface in lta_semantics.interfaces:
        assert interface.generic_signature.ring_size == interface.ring_size
        assert interface.unordered_tile_labels == tuple(
            sorted((interface.side_a_tile_label, interface.side_b_tile_label))
        )


def test_semantic_interfaces_preserve_oriented_sides_and_periodic_translations(
    lta_geometry,
    lta_semantics,
):
    for source, semantic in zip(lta_geometry.windows, lta_semantics.interfaces, strict=True):
        assert semantic.window_index == source.window_index
        assert semantic.face_index == source.face_index
        assert semantic.face_digest == source.face_digest
        assert semantic.side_a == source.side_a
        assert semantic.side_b == source.side_b
        assert semantic.relative_tile_translation == source.relative_tile_translation
        assert semantic.self_adjacent == source.self_adjacent


def test_generic_registry_uses_machine_readable_signatures_without_conventional_names(
    lta_geometry,
):
    generic = build_framework_semantic_catalog(lta_geometry)
    assert generic.profile is None
    assert generic.profile_id == "generic"
    assert generic.validation is None
    assert all(tile.semantic_label is None for tile in generic.tiles)
    assert all(tile.generic_label.startswith("tile:") for tile in generic.tiles)
    assert all(interface.family_label is None for interface in generic.interfaces)
    assert all(interface.generic_label.startswith("interface:") for interface in generic.interfaces)
    assert Counter(interface.generic_signature.ring_size for interface in generic.interfaces) == {
        4: 36,
        6: 16,
        8: 6,
    }


def test_expected_counts_validate_but_do_not_define_local_classification(lta_geometry):
    wrong = FrameworkSemanticProfile(
        "lta_wrong_count",
        "LTA profile with deliberately wrong count",
        tuple(
            TileSemanticRule(
                rule.signature,
                rule.semantic_label,
                rule.display_label,
                rule.role,
                5 if rule.semantic_label == "d4r" else rule.expected_count,
            )
            for rule in LTA_FRAMEWORK_PROFILE.tile_rules
        ),
        LTA_FRAMEWORK_PROFILE.interface_rules,
        LTA_FRAMEWORK_PROFILE.references,
    )
    with pytest.raises(FrameworkSemanticsInvariantError, match="multiplicity validation"):
        build_framework_semantic_catalog(lta_geometry, profile=wrong)


def test_lta_profile_is_not_forced_onto_a_non_lta_periodic_tiling():
    fixture = _simple_cubic_fixture()
    cube = build_tiling_geometry_catalog(fixture.complex, fixture.embedding, fixture.ring_index)
    generic = build_framework_semantic_catalog(cube)
    assert generic.tiles[0].face_signature == TileFaceSignature(((4, 6),))
    assert all(interface.generic_signature == RingInterfaceSignature(4, (TileFaceSignature(((4, 6),)),) * 2) for interface in generic.interfaces)
    with pytest.raises(FrameworkSemanticsInvariantError, match="no interface rule"):
        build_framework_semantic_catalog(cube, profile=LTA_FRAMEWORK_PROFILE)


def test_profile_rules_are_extensible_and_canonical():
    profile = FrameworkSemanticProfile(
        "toy",
        "Toy profile",
        (TileSemanticRule(TileFaceSignature(((4, 6),)), "cube", "cube", "cage", 1),),
        (RingInterfaceRule(4, ("cube", "cube"), "cube_face", "cube face", "window", 3),),
        ("test-only profile",),
    )
    assert FrameworkSemanticProfile.from_dict(profile.to_dict()) == profile
    fixture = _simple_cubic_fixture()
    cube = build_tiling_geometry_catalog(fixture.complex, fixture.embedding, fixture.ring_index)
    catalog = build_framework_semantic_catalog(cube, profile=profile)
    assert Counter(value.semantic_label for value in catalog.tiles) == {"cube": 1}
    assert Counter(value.family_label for value in catalog.interfaces) == {"cube_face": 3}


def test_resource_preflight_is_transactional(lta_geometry):
    with pytest.raises(FrameworkSemanticsResourceError, match="max_tiles"):
        build_framework_semantic_catalog(
            lta_geometry,
            profile=LTA_FRAMEWORK_PROFILE,
            resources=FrameworkSemanticsResources(max_tiles=1),
        )
    with pytest.raises(FrameworkSemanticsResourceError, match="max_windows"):
        build_framework_semantic_catalog(
            lta_geometry,
            profile=LTA_FRAMEWORK_PROFILE,
            resources=FrameworkSemanticsResources(max_windows=1),
        )
    with pytest.raises(FrameworkSemanticsResourceError, match="max_profile_rules"):
        build_framework_semantic_catalog(
            lta_geometry,
            profile=LTA_FRAMEWORK_PROFILE,
            resources=FrameworkSemanticsResources(max_profile_rules=1),
        )


def test_source_replay_and_tamper_rejection(lta_geometry, lta_semantics):
    assert FrameworkSemanticCatalog.from_dict(
        lta_semantics.to_dict(), geometry=lta_geometry
    ) == lta_semantics
    tampered = deepcopy(lta_semantics.to_dict())
    tampered["interfaces"][0]["family_label"] = "d4r_beta_4r"
    with pytest.raises(FrameworkSemanticsSerializationError):
        FrameworkSemanticCatalog.from_dict(tampered, geometry=lta_geometry)


def test_constructor_and_public_export_contracts(lta_geometry):
    for name in (
        "FrameworkSemanticCatalog",
        "FrameworkSemanticProfile",
        "LTA_FRAMEWORK_PROFILE",
        "TileFaceSignature",
        "RingInterfaceSignature",
        "build_framework_semantic_catalog",
    ):
        assert hasattr(analysis, name)
        assert name in analysis.__all__
    with pytest.raises(FrameworkSemanticsInputError):
        build_framework_semantic_catalog(object())
    with pytest.raises(FrameworkSemanticsInputError):
        TileFaceSignature(((6, 1), (4, 1)))
    with pytest.raises(FrameworkSemanticsInputError):
        FrameworkSemanticsResources(max_tiles=True)
