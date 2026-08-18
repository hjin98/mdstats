from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math

import numpy as np
import pytest

import mdstats.analysis as analysis
from mdstats.analysis import (
    ReferenceRingGeometryCatalog,
    RingGeometryInputError,
    RingGeometryOptions,
    RingGeometryResourceError,
    RingGeometryResources,
    RingGeometrySerializationError,
    RingGeometryStatus,
    build_reference_ring_geometry_catalog,
)
from mdstats.analysis.atomic_connectivity import (
    ConnectivityScope,
    ExplicitConnectivity,
    compute_atomic_connectivity,
)

from tests._ring_geometry_fixture import (
    lta_reference_ring_geometry_fixture,
    make_framework_connectivity,
    make_lta_collection,
)


@pytest.fixture(scope="module")
def lta_ring_fixture():
    return lta_reference_ring_geometry_fixture()


def _build_for_collection(collection, *, options=None, resources=None):
    topology, reference, geometry = lta_reference_ring_geometry_fixture()[:3]
    connectivity = make_framework_connectivity(collection)
    return build_reference_ring_geometry_catalog(
        geometry,
        reference.complex,
        reference.ring_index,
        topology,
        collection,
        connectivity,
        options=options,
        resources=resources,
    )


def test_real_lta_reference_resolves_all_chemical_ring_polygons(lta_ring_fixture):
    _topology, _reference, _geometry, _collection, _connectivity, catalog = lta_ring_fixture
    assert len(catalog.rings) == 58
    assert catalog.resolved_count == 58
    assert catalog.unresolved_count == 0
    assert Counter(ring.ring_size for ring in catalog.rings) == {4: 36, 6: 16, 8: 6}
    assert Counter(ring.status for ring in catalog.rings) == {
        RingGeometryStatus.RESOLVED: 58
    }
    assert not catalog.source_connectivity_exact_match
    assert len(catalog.framework_path_binding_digest) == 64


def test_resolved_lta_rings_bind_one_oxygen_to_every_t_t_edge(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, catalog = lta_ring_fixture
    for ring in catalog.rings:
        assert len(ring.t_atom_refs) == ring.ring_size
        assert len(ring.o_atom_refs) == ring.ring_size
        assert len({ref.atom_index for ref in ring.o_atom_refs}) == ring.ring_size
        assert all(collection.atomic_numbers[ref.atom_index] == 8 for ref in ring.o_atom_refs)
        assert all(distance > 0.0 for distance in ring.t_o_distances)
        assert all(distance > 0.0 for distance in ring.o_t_distances)


def test_oxygen_area_center_is_authoritative_geometric_center(lta_ring_fixture):
    _topology, _reference, geometry, _collection, _connectivity, catalog = lta_ring_fixture
    center_differences = []
    vertex_area_differences = []
    for window, ring in zip(geometry.windows, catalog.rings, strict=True):
        assert ring.geometric_center == ring.oxygen_area_centroid
        center_differences.append(
            np.linalg.norm(
                np.asarray(ring.oxygen_area_centroid)
                - np.asarray(window.cartesian_center)
            )
        )
        vertex_area_differences.append(
            np.linalg.norm(
                np.asarray(ring.oxygen_area_centroid)
                - np.asarray(ring.oxygen_vertex_centroid)
            )
        )
    assert max(center_differences) > 0.05
    assert max(vertex_area_differences) > 1.0e-4


def test_side_frames_are_opposite_orthonormal_and_right_handed(lta_ring_fixture):
    _topology, _reference, _geometry, _collection, _connectivity, catalog = lta_ring_fixture
    for ring in catalog.rings:
        first, second = ring.side_frames
        n0 = np.asarray(first.inward_unit_normal)
        n1 = np.asarray(second.inward_unit_normal)
        assert np.allclose(n0, -n1, rtol=0.0, atol=1.0e-10)
        for side in ring.side_frames:
            normal = np.asarray(side.inward_unit_normal)
            axis_u = np.asarray(side.axis_u)
            axis_v = np.asarray(side.axis_v)
            assert np.allclose(np.linalg.norm(normal), 1.0)
            assert np.allclose(np.linalg.norm(axis_u), 1.0)
            assert np.allclose(np.linalg.norm(axis_v), 1.0)
            assert np.dot(normal, axis_u) == pytest.approx(0.0, abs=1.0e-10)
            assert np.dot(normal, axis_v) == pytest.approx(0.0, abs=1.0e-10)
            assert np.dot(axis_u, axis_v) == pytest.approx(0.0, abs=1.0e-10)
            assert np.dot(np.cross(axis_u, axis_v), normal) == pytest.approx(1.0)


def test_side_normals_point_into_the_incident_natural_tiles(lta_ring_fixture):
    _topology, _reference, geometry, _collection, _connectivity, catalog = lta_ring_fixture
    face_by_side = {face.side: face for face in geometry.tile_faces}
    for ring in catalog.rings:
        for side_frame in ring.side_frames:
            tile_face = face_by_side[side_frame.side]
            inward = np.asarray(side_frame.inward_unit_normal)
            t_face_inward = -np.asarray(tile_face.outward_unit_normal)
            assert np.dot(inward, t_face_inward) > 0.98


def test_reference_descriptors_are_finite_and_physically_ordered(lta_ring_fixture):
    _topology, _reference, _geometry, _collection, _connectivity, catalog = lta_ring_fixture
    for ring in catalog.rings:
        assert ring.projected_area > 0.0
        assert ring.vector_area_magnitude > 0.0
        assert ring.perimeter > 0.0
        assert ring.center_aperture_radius >= 0.0
        assert ring.planarity_rms >= 0.0
        assert ring.planarity_max >= ring.planarity_rms
        assert ring.puckering_amplitude >= ring.planarity_max
        assert ring.ellipticity >= 1.0
        assert tuple(sorted(ring.covariance_eigenvalues)) == ring.covariance_eigenvalues
        assert all(math.isfinite(value) for value in ring.covariance_eigenvalues)


def test_per_atom_integer_wrapping_does_not_change_intrinsic_ring_geometry(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, baseline = lta_ring_fixture
    shifted = np.asarray(collection.fractional_positions[0]).copy()
    integer_shifts = np.zeros_like(shifted)
    integer_shifts[::3, 0] = 2
    integer_shifts[1::4, 1] = -1
    integer_shifts[2::5, 2] = 3
    shifted += integer_shifts
    rebuilt = _build_for_collection(make_lta_collection(fractional_positions=shifted))
    assert rebuilt.reference_frame_digest != baseline.reference_frame_digest
    for first, second in zip(baseline.rings, rebuilt.rings, strict=True):
        assert second.projected_area == pytest.approx(first.projected_area)
        assert second.perimeter == pytest.approx(first.perimeter)
        assert second.planarity_rms == pytest.approx(first.planarity_rms)
        assert second.center_aperture_radius == pytest.approx(first.center_aperture_radius)
        assert np.allclose(second.oxygen_area_centroid, first.oxygen_area_centroid)


def test_origin_translation_shifts_centers_but_preserves_intrinsic_geometry(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, baseline = lta_ring_fixture
    translation = np.asarray([1.25, -0.75, 2.5])
    translated = _build_for_collection(
        make_lta_collection(
            fractional_positions=collection.fractional_positions[0],
            cell=collection.cells[0],
            origin=translation,
        )
    )
    for first, second in zip(baseline.rings, translated.rings, strict=True):
        assert np.allclose(
            np.asarray(second.oxygen_area_centroid),
            np.asarray(first.oxygen_area_centroid) + translation,
        )
        assert second.projected_area == pytest.approx(first.projected_area)
        assert second.perimeter == pytest.approx(first.perimeter)
        assert np.allclose(second.ordered_unit_normal, first.ordered_unit_normal)


def test_rigid_rotation_transforms_centers_and_normals_covariantly(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, baseline = lta_ring_fixture
    rotation = np.asarray(
        [[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    rotated = _build_for_collection(
        make_lta_collection(
            fractional_positions=collection.fractional_positions[0],
            cell=collection.cells[0] @ rotation,
        )
    )
    for first, second in zip(baseline.rings, rotated.rings, strict=True):
        assert np.allclose(
            second.oxygen_area_centroid,
            np.asarray(first.oxygen_area_centroid) @ rotation,
            atol=1.0e-10,
        )
        assert np.allclose(
            second.ordered_unit_normal,
            np.asarray(first.ordered_unit_normal) @ rotation,
            atol=1.0e-10,
        )
        assert second.projected_area == pytest.approx(first.projected_area)
        assert second.perimeter == pytest.approx(first.perimeter)


def test_uniform_scaling_has_correct_descriptor_homogeneity(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, baseline = lta_ring_fixture
    scale = 1.7
    scaled = _build_for_collection(
        make_lta_collection(
            fractional_positions=collection.fractional_positions[0],
            cell=collection.cells[0] * scale,
        )
    )
    for first, second in zip(baseline.rings, scaled.rings, strict=True):
        assert second.projected_area == pytest.approx(first.projected_area * scale**2)
        assert second.vector_area_magnitude == pytest.approx(first.vector_area_magnitude * scale**2)
        assert second.perimeter == pytest.approx(first.perimeter * scale)
        assert second.planarity_rms == pytest.approx(first.planarity_rms * scale)
        assert second.center_aperture_radius == pytest.approx(first.center_aperture_radius * scale)
        assert second.ellipticity == pytest.approx(first.ellipticity)
        assert np.allclose(second.ordered_unit_normal, first.ordered_unit_normal)


def test_wrong_bridge_species_produces_explicit_unresolved_records(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, _catalog = lta_ring_fixture
    unresolved = _build_for_collection(
        collection,
        options=RingGeometryOptions(oxygen_atomic_number=7),
    )
    assert unresolved.resolved_count == 0
    assert unresolved.unresolved_count == 58
    assert {ring.status for ring in unresolved.rings} == {
        RingGeometryStatus.MISSING_OR_AMBIGUOUS_OXYGEN_BRIDGE
    }
    assert all(not ring.t_atom_refs and ring.geometric_center is None for ring in unresolved.rings)


def test_missing_framework_atomic_edge_fails_before_ring_construction(lta_ring_fixture):
    topology, reference, geometry, collection, connectivity, _catalog = lta_ring_fixture
    active = tuple(int(value) for value in connectivity.resolved_scope.atom_indices)
    incomplete = compute_atomic_connectivity(
        collection,
        ExplicitConnectivity(
            scope=ConnectivityScope.from_selection(included_atom_indices=active),
            uniform_edges=connectivity.states[0].edge_keys[:-1],
        ),
    )
    with pytest.raises(RingGeometryInputError, match="cannot replay every framework"):
        build_reference_ring_geometry_catalog(
            geometry,
            reference.complex,
            reference.ring_index,
            topology,
            collection,
            incomplete,
        )


def test_strict_complete_source_binding_rejects_framework_only_state(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, _catalog = lta_ring_fixture
    with pytest.raises(RingGeometryInputError, match="complete connectivity state"):
        _build_for_collection(
            collection,
            options=RingGeometryOptions(require_exact_source_connectivity=True),
        )


def test_resource_preflight_is_transactional(lta_ring_fixture):
    _topology, _reference, _geometry, collection, _connectivity, _catalog = lta_ring_fixture
    with pytest.raises(RingGeometryResourceError, match="max_windows"):
        _build_for_collection(
            collection,
            resources=RingGeometryResources(max_windows=10),
        )


def test_source_replay_and_tamper_detection(lta_ring_fixture):
    topology, reference, geometry, collection, connectivity, catalog = lta_ring_fixture
    replayed = ReferenceRingGeometryCatalog.from_dict(
        catalog.to_dict(),
        tiling_geometry=geometry,
        complex_=reference.complex,
        ring_index=reference.ring_index,
        topology=topology,
        collection=collection,
        connectivity=connectivity,
    )
    assert replayed == catalog
    payload = deepcopy(catalog.to_dict())
    payload["rings"][0]["projected_area"] += 0.5
    with pytest.raises(RingGeometrySerializationError):
        ReferenceRingGeometryCatalog.from_dict(
            payload,
            tiling_geometry=geometry,
            complex_=reference.complex,
            ring_index=reference.ring_index,
            topology=topology,
            collection=collection,
            connectivity=connectivity,
        )


def test_analysis_exports_stage_11c1_api():
    assert analysis.ReferenceRingGeometry is not None
    assert analysis.ReferenceRingGeometryCatalog is not None
    assert analysis.RingSideFrame is not None
    assert analysis.build_reference_ring_geometry_catalog is build_reference_ring_geometry_catalog
