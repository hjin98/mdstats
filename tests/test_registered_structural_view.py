from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import math

import numpy as np
import pytest

import mdstats
import mdstats.analysis as analysis
from mdstats.analysis import (
    FrameNaturalTileGeometry,
    FrameTileFaceGeometry,
    FrameTilingGeometryCatalog,
    FrameTilingGeometryOptions,
    FrameTilingGeometryResources,
    FrameTilingGeometryStatus,
    FrameWindowGeometry,
    MappedTilingFrame,
    RegisteredRingViewStatus,
    RegisteredStructuralFrameStatus,
    RegisteredStructuralGeometryView,
    RegisteredStructuralViewOptions,
    RegisteredStructuralViewResourceError,
    RegisteredStructuralViewResources,
    RegisteredStructuralViewSerializationError,
    RegisteredStructuralViewSourceError,
    build_registered_structural_geometry_view,
    build_structural_ring_boundary_catalog,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    FrameRegistrationPolicy,
    LatticeGaugeOptions,
    ReferenceCellDefinition,
    RegistrationSpatialPolicy,
    prepare_frame_registration,
    prepare_source_coordinate_contract,
)
from mdstats.semantics import FrameSemantics

from tests._ring_geometry_fixture import lta_reference_ring_geometry_fixture
from tests.test_stage11c3_ring_boundary import _mapped_catalog


@pytest.fixture(scope="module")
def lta_sources():
    _topology, _tiling, _geometry, collection, _connectivity, reference = (
        lta_reference_ring_geometry_fixture()
    )
    mapped = _mapped_catalog(reference)
    boundaries = build_structural_ring_boundary_catalog(
        reference, mapped, collection
    )
    return collection, reference, mapped, boundaries


def _identity_view(lta_sources):
    collection, _reference, mapped, boundaries = lta_sources
    registration = prepare_frame_registration(collection)
    view = build_registered_structural_geometry_view(
        collection, registration, mapped, boundaries
    )
    return collection, registration, view


def test_identity_registration_preserves_c3_identities_and_coordinates(lta_sources):
    collection, registration, view = _identity_view(lta_sources)
    assert view.registration_signature == registration.signature
    assert len(view.frames) == 1
    frame = view.frames[0]
    assert frame.status is RegisteredStructuralFrameStatus.RESOLVED
    assert len(frame.rings) == 58
    assert frame.resolved_ring_count == 58
    for ring in frame.rings:
        assert ring.status is RegisteredRingViewStatus.RESOLVED
        assert ring.physical is not None and ring.registered is not None
        assert ring.registered.frame.orthonormality_error < 1.0e-10
        for atom in (*ring.registered.t_atoms, *ring.registered.o_atoms):
            np.testing.assert_allclose(
                atom.registered_cartesian, atom.physical_cartesian, atol=2.0e-9
            )
            assert atom.periodic_image_residual < 2.0e-9
            reconstructed = (
                np.asarray(atom.registered_fractional_wrapped)
                + np.floor(np.asarray(atom.registered_fractional_unwrapped))
            ) @ registration.registered_cells[0]
            np.testing.assert_allclose(
                reconstructed, atom.registered_cartesian, atol=2.0e-9
            )
    assert view.collection_binding_digest
    assert collection.n_atoms == registration.registered_unwrapped_cartesian.shape[1]


def test_nonrigid_affine_map_reconstructs_orthonormal_frames_without_changing_physical_metrics(
    lta_sources,
):
    collection, _reference, mapped, boundaries = lta_sources
    affine = np.asarray(
        [[1.12, 0.31, 0.07], [0.0, 0.91, 0.22], [0.0, 0.0, 1.08]],
        dtype=np.float64,
    )
    reference_cell = ReferenceCellDefinition.explicit_matrix(
        collection.cells[0] @ affine
    )
    registration = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(
            spatial_policy=RegistrationSpatialPolicy.REFERENCE_MATERIAL
        ),
        reference_cell=reference_cell,
    )
    view = build_registered_structural_geometry_view(
        collection, registration, mapped, boundaries
    )
    axis_errors = []
    for source, ring in zip(mapped.frames[0].rings, view.frames[0].rings, strict=True):
        assert ring.status is RegisteredRingViewStatus.RESOLVED
        assert ring.physical is not None and ring.registered is not None
        np.testing.assert_array_equal(ring.physical.t_o_distances, source.t_o_distances)
        np.testing.assert_array_equal(ring.physical.o_t_distances, source.o_t_distances)
        assert ring.physical.center_aperture_radius == source.center_aperture_radius
        basis = np.asarray(
            [
                ring.registered.frame.axis_u,
                ring.registered.frame.axis_v,
                ring.registered.frame.ordered_unit_normal,
            ]
        )
        np.testing.assert_allclose(basis @ basis.T, np.eye(3), atol=2.0e-9)
        axis_errors.append(
            ring.registered.frame.transformed_physical_axes_orthogonality_error
        )
        for atom in (*ring.registered.t_atoms, *ring.registered.o_atoms):
            expected = np.asarray(atom.physical_cartesian) @ affine
            np.testing.assert_allclose(
                atom.registered_cartesian, expected, atol=3.0e-9
            )
    assert max(axis_errors) > 1.0e-2


def test_periodic_ring_images_are_certified_against_registered_base_atoms(lta_sources):
    _collection, registration, view = _identity_view(lta_sources)
    atoms = [
        atom
        for ring in view.frames[0].rings
        if ring.registered is not None
        for atom in (*ring.registered.t_atoms, *ring.registered.o_atoms)
        if atom.atom_ref.image_shift != (0, 0, 0)
    ]
    assert atoms, "The LTA ring catalog should contain nonzero periodic images."
    for atom in atoms:
        base = registration.registered_unwrapped_cartesian[0, atom.atom_ref.atom_index]
        reconstructed = base + np.asarray(atom.registered_image_shift) @ registration.registered_cells[0]
        np.testing.assert_allclose(reconstructed, atom.registered_cartesian, atol=2.0e-9)
        assert atom.periodic_image_residual < 2.0e-9


def _minimal_tiling_catalog(collection: AtomisticFrameCollection) -> FrameTilingGeometryCatalog:
    center = np.asarray([1.2, 1.1, 0.8])
    vertices = (
        (0.8, 0.8, 0.8),
        (1.8, 0.8, 0.8),
        (1.2, 1.7, 0.8),
    )
    face = FrameTileFaceGeometry(
        side_index=0,
        fractional_vertices=tuple(
            tuple(float(value) for value in np.asarray(point) @ np.linalg.inv(collection.cells[0]))
            for point in vertices
        ),
        cartesian_vertices=vertices,
        fractional_center=tuple(float(value) for value in center @ np.linalg.inv(collection.cells[0])),
        cartesian_center=tuple(float(value) for value in center),
        area_weighted_unit_normal=(0.0, 0.0, 1.0),
        area=0.45,
        perimeter=3.1,
        planarity_rms=0.0,
        planarity_max=0.0,
        projected_aperture_radius=0.25,
        planar_aperture_certified=True,
    )
    tile = FrameNaturalTileGeometry(
        tile_index=0,
        fractional_center=tuple(float(value) for value in center @ np.linalg.inv(collection.cells[0])),
        cartesian_center=tuple(float(value) for value in center),
        signed_volume=1.0,
        volume=1.0,
        surface_area=6.0,
        equivalent_sphere_radius=0.62,
        sphericity=0.8,
        diameter=1.9,
        orientation_preserved=True,
    )
    window = FrameWindowGeometry(
        window_index=0,
        cartesian_center=tuple(float(value) for value in center),
        area=0.45,
        side_area_mismatch=0.0,
        projected_aperture_radius=0.25,
        planarity_rms=0.0,
        planarity_max=0.0,
        planar_aperture_certified=True,
    )
    mapped = MappedTilingFrame(
        result_position=0,
        collection_frame_index=0,
        frame_id=int(collection.frame_ids[0]),
        step=None,
        time=None,
        status=FrameTilingGeometryStatus.MAPPED,
        topology_graph_digest="a" * 64,
        connectivity_state_digest="b" * 64,
        global_image_shift=(0, 0, 0),
        vertex_atom_indices=(),
        vertex_image_gauges=(),
        tiles=(tile,),
        tile_faces=(face,),
        windows=(window,),
        cell_volume=float(abs(np.linalg.det(collection.cells[0]))),
        total_tile_volume=1.0,
        volume_closure_error=0.0,
    )
    return FrameTilingGeometryCatalog(
        reference_geometry_digest="1" * 64,
        periodic_cell_complex_digest="2" * 64,
        periodic_net_embedding_digest="3" * 64,
        primitive_ring_catalog_digest="4" * 64,
        topology_catalog_digest="5" * 64,
        collection_geometry_digest="6" * 64,
        connectivity_binding_digest="7" * 64,
        options=FrameTilingGeometryOptions(),
        resources=FrameTilingGeometryResources(),
        frames=(mapped,),
    )


def test_optional_tile_cage_face_and_window_embeddings_keep_physical_metrics(lta_sources):
    collection, _reference, mapped, boundaries = lta_sources
    affine = np.asarray(
        [[1.0, 0.25, 0.0], [0.0, 1.0, 0.15], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    registration = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(
            spatial_policy=RegistrationSpatialPolicy.REFERENCE_MATERIAL
        ),
        reference_cell=ReferenceCellDefinition.explicit_matrix(
            collection.cells[0] @ affine
        ),
    )
    tiling = _minimal_tiling_catalog(collection)
    view = build_registered_structural_geometry_view(
        collection,
        registration,
        mapped,
        boundaries,
        frame_tiling_geometry=tiling,
    )
    frame = view.frames[0]
    assert frame.status is RegisteredStructuralFrameStatus.RESOLVED
    assert len(frame.tiles) == len(frame.tile_faces) == len(frame.windows) == 1
    tile = frame.tiles[0]
    np.testing.assert_allclose(
        tile.registered_center, np.asarray(tile.physical_center) @ affine
    )
    assert tile.structural_role == "natural_tile_cage"
    assert tile.physical_volume == 1.0
    face = frame.tile_faces[0]
    np.testing.assert_allclose(
        face.registered_vertices,
        np.asarray(face.physical_vertices) @ affine,
    )
    assert math.isclose(np.linalg.norm(face.registered_unit_normal), 1.0)
    assert face.physical_area == 0.45
    assert frame.windows[0].physical_projected_aperture_radius == 0.25


def _two_frame_collection(base: AtomisticFrameCollection, rotation: np.ndarray, semantics: FrameSemantics):
    cells = np.stack((base.cells[0], base.cells[0] @ rotation.T))
    fractional = np.stack((base.fractional_positions[0], base.fractional_positions[0]))
    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.asarray([0, 1], dtype=np.int64),
        atomic_numbers=base.atomic_numbers,
        masses=base.masses,
        pbc=base.pbc,
        steps=np.asarray([0, 1], dtype=np.int64) if semantics is FrameSemantics.TRAJECTORY else None,
        times=np.asarray([0.0, 1.0], dtype=np.float64) if semantics is FrameSemantics.TRAJECTORY else None,
        cells=cells,
        origins=np.zeros((2, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=(
            np.zeros((2, base.n_atoms, 3), dtype=np.float64)
            if semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        provenance=(
            replace(
                base.provenance,
                velocity_source="native",
                coordinate_normalization="native_unwrapped_fractional",
            )
            if semantics is FrameSemantics.TRAJECTORY
            else base.provenance
        ),
        metadata={},
    )


def _wide_gauge_contract(collection):
    return prepare_source_coordinate_contract(
        collection,
        lattice_options=LatticeGaugeOptions(continuity_relative_tolerance=10.0),
    )


def test_trajectory_orientation_continuity_honors_segment_resets_and_ensemble_semantics(lta_sources):
    base, reference, _mapped, _boundaries = lta_sources
    angle = math.pi / 2.0
    rotation = np.asarray(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    mapped = _mapped_catalog(reference, rotations=(np.eye(3), rotation))

    trajectory = _two_frame_collection(base, rotation, FrameSemantics.TRAJECTORY)
    boundaries = build_structural_ring_boundary_catalog(reference, mapped, trajectory)
    no_reset_registration = prepare_frame_registration(
        trajectory, source_contract=_wide_gauge_contract(trajectory)
    )
    strict = RegisteredStructuralViewOptions(minimum_orientation_continuity_dot=0.99)
    no_reset = build_registered_structural_geometry_view(
        trajectory,
        no_reset_registration,
        mapped,
        boundaries,
        options=strict,
    )
    assert no_reset.frames[1].status in {RegisteredStructuralFrameStatus.PARTIAL, RegisteredStructuralFrameStatus.UNRESOLVED}
    assert any(
        ring.status is RegisteredRingViewStatus.ORIENTATION_DISCONTINUITY
        for ring in no_reset.frames[1].rings
    )

    reset_registration = prepare_frame_registration(
        trajectory,
        source_contract=_wide_gauge_contract(trajectory),
        policy=FrameRegistrationPolicy(segment_reset_frame_indices=(1,)),
    )
    reset_view = build_registered_structural_geometry_view(
        trajectory, reset_registration, mapped, boundaries, options=strict
    )
    assert reset_view.frames[1].resolved_ring_count == 58

    ensemble = _two_frame_collection(base, rotation, FrameSemantics.ENSEMBLE)
    ensemble_boundaries = build_structural_ring_boundary_catalog(reference, mapped, ensemble)
    ensemble_registration = prepare_frame_registration(
        ensemble, source_contract=_wide_gauge_contract(ensemble)
    )
    ensemble_view = build_registered_structural_geometry_view(
        ensemble,
        ensemble_registration,
        mapped,
        ensemble_boundaries,
        options=strict,
    )
    assert ensemble_view.frames[1].resolved_ring_count == 58
    assert all(
        ring.registered is None
        or ring.registered.frame.normal_continuity_dot is None
        for ring in ensemble_view.frames[1].rings
    )


def test_source_mismatch_resource_preflight_serialization_and_public_exports(lta_sources):
    collection, _reference, mapped, boundaries = lta_sources
    registration = prepare_frame_registration(collection)
    view = build_registered_structural_geometry_view(
        collection, registration, mapped, boundaries
    )
    rebuilt = RegisteredStructuralGeometryView.from_dict(
        view.to_dict(),
        collection=collection,
        registration=registration,
        frame_ring_geometry=mapped,
        ring_boundaries=boundaries,
    )
    assert rebuilt == view

    payload = deepcopy(view.to_dict())
    payload["frames"][0]["rings"][0]["registered"]["frame"]["center"][0] += 0.1
    with pytest.raises(RegisteredStructuralViewSerializationError):
        RegisteredStructuralGeometryView.from_dict(
            payload,
            collection=collection,
            registration=registration,
            frame_ring_geometry=mapped,
            ring_boundaries=boundaries,
        )

    with pytest.raises(RegisteredStructuralViewResourceError, match="max_ring_instances"):
        build_registered_structural_geometry_view(
            collection,
            registration,
            mapped,
            boundaries,
            resources=RegisteredStructuralViewResources(max_ring_instances=1),
        )

    shifted = AtomisticFrameCollection(
        frame_semantics=collection.frame_semantics,
        frame_ids=collection.frame_ids,
        atomic_numbers=collection.atomic_numbers,
        masses=collection.masses,
        pbc=collection.pbc,
        steps=collection.steps,
        times=collection.times,
        cells=collection.cells,
        origins=collection.origins,
        fractional_positions=collection.fractional_positions + 0.02,
        provenance=collection.provenance,
        metadata={},
    )
    wrong_registration = prepare_frame_registration(shifted)
    with pytest.raises(RegisteredStructuralViewSourceError, match="registered lattice"):
        build_registered_structural_geometry_view(
            collection, wrong_registration, mapped, boundaries
        )

    assert analysis.build_registered_structural_geometry_view is build_registered_structural_geometry_view
    assert mdstats.RegisteredStructuralGeometryView is RegisteredStructuralGeometryView
    assert "RegisteredStructuralGeometryView" in analysis.__all__
