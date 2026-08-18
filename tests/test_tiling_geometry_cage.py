from __future__ import annotations

from collections import Counter
from copy import deepcopy
from fractions import Fraction

import pytest

from mdstats.analysis import (
    AccessibilityProbe,
    CageAccessibilityCatalog,
    PeriodicObstacleSphere,
    TilingGeometryCatalog,
    TilingGeometryInputError,
    TilingGeometryResourceError,
    TilingGeometryResources,
    TilingGeometrySerializationError,
    WitnessAccessibilityStatus,
    assess_cage_accessibility,
    build_tiling_geometry_catalog,
)
from mdstats.analysis.cage import CageAnalysisSerializationError
from tests.test_periodic_cell_complex import _simple_cubic_fixture
from tests._lta_tiling_fixture import lta_reference_geometry

F = Fraction


@pytest.fixture(scope="module")
def cubic_geometry():
    fixture = _simple_cubic_fixture()
    geometry = build_tiling_geometry_catalog(
        fixture.complex, fixture.embedding, fixture.ring_index
    )
    return fixture, geometry


def test_reference_cube_geometry_is_exact_and_mesh_independent(cubic_geometry):
    _fixture, geometry = cubic_geometry
    assert geometry.total_fractional_volume == 1
    assert len(geometry.tiles) == 1
    assert len(geometry.tile_faces) == 6
    assert len(geometry.windows) == 3
    assert len(geometry.adjacency_arcs) == 6
    tile = geometry.tiles[0]
    assert tile.fractional_center == (F(1, 2), F(1, 2), F(1, 2))
    assert tile.fractional_volume == 1
    assert tile.vertex_count == 8
    assert tile.edge_count == 12
    assert tile.face_count == 6
    assert tile.surface_area == pytest.approx(6.0)
    assert tile.diameter == pytest.approx(3.0**0.5)
    assert tile.convex_certified


def test_topological_windows_preserve_self_image_adjacency(cubic_geometry):
    _fixture, geometry = cubic_geometry
    assert all(window.self_adjacent for window in geometry.windows)
    assert {window.relative_tile_translation for window in geometry.windows} == {
        (-1, 0, 0),
        (0, -1, 0),
        (0, 0, -1),
    }
    assert all(window.area == pytest.approx(1.0) for window in geometry.windows)
    assert all(
        window.aperture_witness_radius == pytest.approx(0.5)
        for window in geometry.windows
    )
    assert {
        arc.target_image_shift for arc in geometry.adjacency_arcs
    } == {
        (-1, 0, 0),
        (1, 0, 0),
        (0, -1, 0),
        (0, 1, 0),
        (0, 0, -1),
        (0, 0, 1),
    }


def test_obstacle_free_probe_recovers_three_dimensional_accessible_network(cubic_geometry):
    fixture, geometry = cubic_geometry
    result = assess_cage_accessibility(
        geometry, fixture.embedding, AccessibilityProbe(0.4, "guest")
    )
    assert all(cage.accessible for cage in result.cages)
    assert all(portal.accessible for portal in result.portals)
    assert result.accessible_arc_indices == tuple(range(6))
    assert len(result.network_components) == 1
    component = result.network_components[0]
    assert component.translation_rank == 3
    assert component.dimensionality == "three-dimensional-network"


def test_large_probe_blocks_stored_portal_witness_without_claiming_global_inaccessibility(
    cubic_geometry,
):
    fixture, geometry = cubic_geometry
    result = assess_cage_accessibility(
        geometry, fixture.embedding, AccessibilityProbe(0.51)
    )
    assert result.cages[0].accessible
    assert all(
        portal.status is WitnessAccessibilityStatus.WITNESS_BLOCKED_UNRESOLVED
        for portal in result.portals
    )
    assert not result.accessible_arc_indices
    assert result.network_components[0].translation_rank == 0
    assert result.network_components[0].dimensionality == "isolated-cage"


def test_periodic_obstacle_images_are_included_in_witness_clearance(cubic_geometry):
    fixture, geometry = cubic_geometry
    obstacles = (
        PeriodicObstacleSphere(0, (F(1), F(1, 2), F(1, 2)), 0.1, "boundary"),
    )
    result = assess_cage_accessibility(
        geometry,
        fixture.embedding,
        AccessibilityProbe(0.05),
        obstacles,
    )
    blocked = [portal for portal in result.portals if not portal.accessible]
    assert len(blocked) == 1
    assert blocked[0].window_index == 0
    assert blocked[0].limiting_obstacle_id == 0
    assert blocked[0].obstacle_clearance == pytest.approx(-0.1)
    assert result.periodic_image_test_count > 0


def test_obstacle_at_tile_witness_blocks_only_the_witness_claim(cubic_geometry):
    fixture, geometry = cubic_geometry
    result = assess_cage_accessibility(
        geometry,
        fixture.embedding,
        AccessibilityProbe(0.0),
        (PeriodicObstacleSphere(0, (F(1, 2), F(1, 2), F(1, 2)), 0.1),),
    )
    assert result.cages[0].status is WitnessAccessibilityStatus.WITNESS_BLOCKED_UNRESOLVED
    assert result.cages[0].obstacle_clearance == pytest.approx(-0.1)
    assert not result.accessible_arc_indices


def test_tiling_geometry_resource_preflight_is_transactional():
    fixture = _simple_cubic_fixture()
    with pytest.raises(TilingGeometryResourceError, match="max_faces"):
        build_tiling_geometry_catalog(
            fixture.complex,
            fixture.embedding,
            fixture.ring_index,
            resources=TilingGeometryResources(max_faces=2),
        )


def test_geometry_and_accessibility_source_replay_reject_tampering(cubic_geometry):
    fixture, geometry = cubic_geometry
    assert (
        TilingGeometryCatalog.from_dict(
            geometry.to_dict(),
            complex_=fixture.complex,
            embedding=fixture.embedding,
            ring_index=fixture.ring_index,
        )
        == geometry
    )
    payload = deepcopy(geometry.to_dict())
    payload["tiles"][0]["surface_area"] += 1.0
    with pytest.raises(TilingGeometrySerializationError):
        TilingGeometryCatalog.from_dict(
            payload,
            complex_=fixture.complex,
            embedding=fixture.embedding,
            ring_index=fixture.ring_index,
        )

    accessibility = assess_cage_accessibility(
        geometry, fixture.embedding, AccessibilityProbe(0.4)
    )
    assert (
        CageAccessibilityCatalog.from_dict(
            accessibility.to_dict(),
            geometry=geometry,
            embedding=fixture.embedding,
        )
        == accessibility
    )
    payload = deepcopy(accessibility.to_dict())
    payload["accessible_arc_indices"] = []
    with pytest.raises(CageAnalysisSerializationError):
        CageAccessibilityCatalog.from_dict(
            payload,
            geometry=geometry,
            embedding=fixture.embedding,
        )


def test_geometry_rejects_wrong_source_types(cubic_geometry):
    fixture, _geometry = cubic_geometry
    with pytest.raises(TilingGeometryInputError):
        build_tiling_geometry_catalog(
            fixture.complex, fixture.embedding, object()  # type: ignore[arg-type]
        )


def test_real_lta_reference_geometry_recovers_certified_tiles_and_windows():
    _topology, reference, geometry = lta_reference_geometry()
    assert reference.partition.certified
    assert geometry.total_fractional_volume == 1
    assert len(geometry.tiles) == 10
    assert len(geometry.windows) == 58
    assert len(geometry.adjacency_arcs) == 116
    assert Counter(tile.label for tile in geometry.tiles) == {
        "4^6": 6,
        "4^6.6^8": 2,
        "4^12.6^8.8^6": 2,
    }
    assert tuple(sorted(tile.fractional_volume for tile in geometry.tiles)) == tuple(
        sorted(
            (F(1, 256),) * 6
            + (F(61, 768),) * 2
            + (F(157, 384),) * 2
        )
    )
