from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
import pytest

import mdstats.analysis as analysis
from mdstats.analysis import (
    FrameRingGeometry,
    FrameRingGeometryCatalog,
    FrameRingGeometryInputError,
    FrameRingGeometryResourceError,
    FrameRingGeometryResources,
    FrameRingGeometrySerializationError,
    FrameRingGeometryStatus,
    FrameTilingGeometryStatus,
    MappedRingFrameStatus,
    build_reference_ring_geometry_catalog,
    map_ring_geometry_to_frames,
    map_tiling_geometry_to_frames,
)
from mdstats.analysis.atomic_connectivity import AtomicEdgeKey

from tests.test_tiling_geometry_frames import (
    _collection,
    _sources_for_collection,
    lta_frame_sources,
)


@pytest.fixture(scope="module")
def sources():
    return lta_frame_sources.__wrapped__()


def _build(sources, fractional, *, cells=None, frame_edges=None, resources=None):
    collection = _collection(sources, fractional, cells=cells)
    connectivity, topology_catalog = _sources_for_collection(
        sources, collection, frame_edges=frame_edges
    )
    frame_tiling = map_tiling_geometry_to_frames(
        sources.geometry,
        sources.reference.complex,
        sources.reference.embedding,
        sources.reference.ring_index,
        collection,
        connectivity,
        topology_catalog,
    )
    reference = build_reference_ring_geometry_catalog(
        sources.geometry,
        sources.reference.complex,
        sources.reference.ring_index,
        topology_catalog.topology_for_frame(0),
        collection,
        connectivity,
        frame_index=0,
    )
    mapped = map_ring_geometry_to_frames(
        reference,
        frame_tiling,
        collection,
        connectivity,
        resources=resources,
    )
    return collection, connectivity, topology_catalog, frame_tiling, reference, mapped


def test_reference_frame_maps_all_58_rings_and_matches_11c1(sources):
    result = _build(sources, sources.single.fractional_positions.copy())
    reference, mapped = result[-2:]
    assert mapped.mapped_frame_count == 1
    frame = mapped.frames[0]
    assert frame.status is MappedRingFrameStatus.MAPPED
    assert frame.mapped_ring_count == 58
    for static, dynamic in zip(reference.rings, frame.rings, strict=True):
        assert dynamic.status is FrameRingGeometryStatus.MAPPED
        np.testing.assert_allclose(dynamic.o_cartesian_vertices, static.o_cartesian_vertices, atol=2.0e-12)
        np.testing.assert_allclose(dynamic.oxygen_area_centroid, static.oxygen_area_centroid, atol=2.0e-12)
        np.testing.assert_allclose(dynamic.ordered_unit_normal, static.ordered_unit_normal, atol=2.0e-12)
        np.testing.assert_allclose(dynamic.side_frames[0].axis_u, static.side_frames[0].axis_u, atol=2.0e-12)
        assert dynamic.projected_area == pytest.approx(static.projected_area, abs=2.0e-12)
        assert dynamic.tilt_angle_radians == pytest.approx(0.0, abs=2.0e-12)
        assert dynamic.in_plane_rotation_radians == pytest.approx(0.0, abs=2.0e-12)


def test_isotropic_cell_scaling_has_expected_descriptor_powers(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    cells = np.repeat(sources.single.cells, 2, axis=0)
    scale = 1.03
    cells[1] *= scale
    *_, mapped = _build(sources, fractional, cells=cells)
    first, second = mapped.frames
    for a, b in zip(first.rings, second.rings, strict=True):
        assert b.projected_area / a.projected_area == pytest.approx(scale**2, rel=2.0e-11)
        assert b.perimeter / a.perimeter == pytest.approx(scale, rel=2.0e-11)
        assert b.center_aperture_radius / a.center_aperture_radius == pytest.approx(scale, rel=2.0e-11)
        assert b.planarity_rms / scale == pytest.approx(a.planarity_rms, abs=2.0e-11)
        assert b.reference_normal_dot == pytest.approx(1.0, abs=2.0e-12)


def test_integer_wrapping_and_trajectory_anchor_translation_are_continuous(sources):
    fractional = np.repeat(sources.single.fractional_positions, 3, axis=0)
    fractional[1, 0] += np.array([2.0, -1.0, 3.0])
    fractional[1, 70] += np.array([-2.0, 4.0, 1.0])
    fractional[2] += np.array([1.0, 0.0, 0.0])
    *_, mapped = _build(sources, fractional)
    first, wrapped, translated = mapped.frames
    np.testing.assert_allclose(
        [ring.projected_area for ring in wrapped.rings],
        [ring.projected_area for ring in first.rings],
        rtol=2.0e-12,
        atol=2.0e-10,
    )
    cell_vector = sources.single.cells[0, 0]
    for a, b in zip(first.rings, translated.rings, strict=True):
        np.testing.assert_allclose(
            np.asarray(b.oxygen_area_centroid) - np.asarray(a.oxygen_area_centroid),
            cell_vector,
            atol=2.0e-10,
        )
        assert b.projected_area == pytest.approx(a.projected_area, rel=2.0e-12)


def test_rigid_rotation_rotates_centers_normals_and_local_axes(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    cells = np.repeat(sources.single.cells, 2, axis=0)
    angle = 0.25
    rotation = np.asarray(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    cells[1] = cells[0] @ rotation.T
    *_, reference, mapped = _build(sources, fractional, cells=cells)
    second = mapped.frames[1]
    for static, dynamic in zip(reference.rings, second.rings, strict=True):
        np.testing.assert_allclose(
            dynamic.oxygen_area_centroid,
            np.asarray(static.oxygen_area_centroid) @ rotation.T,
            atol=3.0e-10,
        )
        np.testing.assert_allclose(
            dynamic.ordered_unit_normal,
            np.asarray(static.ordered_unit_normal) @ rotation.T,
            atol=3.0e-11,
        )
        np.testing.assert_allclose(
            dynamic.side_frames[0].axis_u,
            np.asarray(static.side_frames[0].axis_u) @ rotation.T,
            atol=3.0e-11,
        )
        assert dynamic.projected_area == pytest.approx(static.projected_area, rel=2.0e-12)


def test_reference_alignment_remains_oriented_under_small_oxygen_deformation(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    oxygen = 72
    fractional[1, oxygen] += np.array([0.004, -0.003, 0.002])
    *_, mapped = _build(sources, fractional)
    second = mapped.frames[1]
    assert second.status is MappedRingFrameStatus.MAPPED
    affected = [ring for ring in second.rings if ring.planarity_max > 1.0e-5]
    assert affected
    for ring in second.rings:
        assert ring.reference_normal_dot >= 0.0
        assert 0.0 <= ring.tilt_angle_radians <= 0.5 * math.pi
        assert math.isfinite(ring.in_plane_rotation_radians)
        first, other = ring.side_frames
        np.testing.assert_allclose(first.inward_unit_normal, -np.asarray(other.inward_unit_normal), atol=1.0e-10)


def test_topology_mismatch_is_inherited_without_mutating_ring_identity(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    damaged = tuple(sources.base_edges[1:])
    *_, frame_tiling, reference, mapped = _build(
        sources,
        fractional,
        frame_edges={0: sources.base_edges, 1: damaged},
    )
    assert frame_tiling.frames[1].status is FrameTilingGeometryStatus.TOPOLOGY_MISMATCH
    frame = mapped.frames[1]
    assert frame.status is MappedRingFrameStatus.UNRESOLVED
    assert all(ring.status is FrameRingGeometryStatus.TOPOLOGY_MISMATCH for ring in frame.rings)
    assert tuple(ring.window_index for ring in frame.rings) == tuple(ring.window_index for ring in reference.rings)
    assert np.isnan(mapped.ring_metric(0, "projected_area")[1])


def test_degenerate_oxygen_polygon_is_explicit_while_other_rings_survive(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    # Build the reference once to identify one persistent O polygon.
    *_, reference0, _mapped0 = _build(sources, fractional[:1])
    ring0 = reference0.rings[0]
    center = np.asarray(ring0.oxygen_area_centroid)
    axis = np.asarray(ring0.side_frames[0].axis_u)
    cell = np.asarray(sources.single.cells[0])
    inverse = np.linalg.inv(cell)
    offsets = np.linspace(-0.15, 0.15, ring0.ring_size)
    for ref, offset in zip(ring0.o_atom_refs, offsets, strict=True):
        fractional[1, ref.atom_index] = (center + offset * axis) @ inverse
    *_, frame_tiling, _reference, mapped = _build(sources, fractional)
    assert frame_tiling.frames[1].status is FrameTilingGeometryStatus.MAPPED
    frame = mapped.frames[1]
    assert frame.status is MappedRingFrameStatus.PARTIALLY_MAPPED
    assert frame.rings[0].status is FrameRingGeometryStatus.DEGENERATE_GEOMETRY
    assert frame.mapped_ring_count > 0


def test_connectivity_geometry_failure_maps_to_ring_gauge_failure(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    fractional[1, 0] += np.array([0.49, 0.0, 0.0])
    *_, frame_tiling, _reference, mapped = _build(sources, fractional)
    assert frame_tiling.frames[1].status is FrameTilingGeometryStatus.CONNECTIVITY_GEOMETRY_MISMATCH
    assert mapped.frames[1].status is MappedRingFrameStatus.UNRESOLVED
    assert all(ring.status is FrameRingGeometryStatus.GAUGE_FAILURE for ring in mapped.frames[1].rings)


def test_resource_preflight_metric_immutability_and_public_exports(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    with pytest.raises(FrameRingGeometryResourceError, match="max_frames"):
        _build(
            sources,
            fractional,
            resources=FrameRingGeometryResources(max_frames=1),
        )
    *_, mapped = _build(sources, fractional)
    series = mapped.ring_metric(0, "projected_area")
    assert not series.flags.writeable
    with pytest.raises(ValueError):
        series[0] = 0.0
    assert analysis.map_ring_geometry_to_frames is map_ring_geometry_to_frames
    assert "FrameRingGeometryCatalog" in analysis.__all__



def test_unresolved_constructor_rejects_partial_geometry():
    with pytest.raises(FrameRingGeometryInputError, match="partial geometry"):
        FrameRingGeometry(
            window_index=0,
            face_index=0,
            primitive_ring_id=0,
            ring_size=4,
            status=FrameRingGeometryStatus.DEGENERATE_GEOMETRY,
            message="degenerate",
            projected_area=1.0,
        )

def test_canonical_source_replay_and_tamper_rejection(sources):
    fractional = np.repeat(sources.single.fractional_positions, 2, axis=0)
    collection, connectivity, _topology, frame_tiling, reference, mapped = _build(
        sources, fractional
    )
    rebuilt = FrameRingGeometryCatalog.from_dict(
        mapped.to_dict(),
        reference_geometry=reference,
        frame_tiling_geometry=frame_tiling,
        collection=collection,
        connectivity=connectivity,
    )
    assert rebuilt == mapped
    payload = deepcopy(mapped.to_dict())
    payload["frames"][0]["rings"][0]["projected_area"] += 1.0
    with pytest.raises(FrameRingGeometrySerializationError):
        FrameRingGeometryCatalog.from_dict(
            payload,
            reference_geometry=reference,
            frame_tiling_geometry=frame_tiling,
            collection=collection,
            connectivity=connectivity,
        )
