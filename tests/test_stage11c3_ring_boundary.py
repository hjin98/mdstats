from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
import pytest

import mdstats
import mdstats.analysis as analysis
from mdstats.analysis import (
    FrameRingGeometry,
    FrameRingGeometryCatalog,
    FrameRingGeometryOptions,
    FrameRingGeometryResources,
    FrameRingGeometryStatus,
    FrameTilingGeometryStatus,
    HarmonicFitStatus,
    LtaOxygenAliasProfile,
    MappedRingFrameStatus,
    MappedRingGeometryFrame,
    RingAtomRef,
    RingSideFrame,
    RingBoundaryAliasError,
    RingBoundaryOptions,
    RingBoundaryResourceError,
    RingBoundaryResources,
    StructuralRingBoundaryCatalog,
    apply_cyclic_dihedral_gauge,
    build_structural_ring_boundary_catalog,
    compute_boundary_measure_angular_moments,
    compute_unweighted_cyclic_index_spectrum,
    fit_physical_angle_harmonics,
    transform_cyclic_coefficient,
)

from tests._ring_geometry_fixture import lta_reference_ring_geometry_fixture


def _origin() -> RingAtomRef:
    return RingAtomRef(0, (0, 0, 0))


def test_alternating_s6r_is_exact_cyclic_nyquist_component():
    spectrum = compute_unweighted_cyclic_index_spectrum(
        [1.0, 2.0, 1.0, 2.0, 1.0, 2.0],
        sequence_name="alternating",
        cyclic_origin_atom=_origin(),
        normalization_scale=1.5,
    )
    assert spectrum.mode(0).coefficient_real == pytest.approx(1.5)
    assert spectrum.mode(1).amplitude == pytest.approx(0.0, abs=1.0e-14)
    assert spectrum.mode(2).amplitude == pytest.approx(0.0, abs=1.0e-14)
    assert spectrum.mode(3).nyquist
    assert spectrum.mode(3).coefficient_real == pytest.approx(-0.5)
    assert spectrum.mode(3).coefficient_imag == pytest.approx(0.0, abs=1.0e-14)
    assert spectrum.mode(3).nyquist_orientation_sign == -1
    assert not spectrum.mode(3).phase_defined


def test_declared_dihedral_transform_matches_recomputed_coefficients():
    values = np.asarray([0.4, 1.2, -0.3, 0.9, 0.1, -0.7])
    base = compute_unweighted_cyclic_index_spectrum(
        values,
        sequence_name="signal",
        cyclic_origin_atom=_origin(),
    )
    for orientation in (1, -1):
        transformed_values = apply_cyclic_dihedral_gauge(
            values, origin_shift=2, orientation=orientation
        )
        transformed = compute_unweighted_cyclic_index_spectrum(
            transformed_values,
            sequence_name="signal",
            cyclic_origin_atom=_origin(),
        )
        for mode in range(4):
            source = complex(base.mode(mode).coefficient_real, base.mode(mode).coefficient_imag)
            expected = transform_cyclic_coefficient(
                source,
                ring_size=6,
                mode=mode,
                origin_shift=2,
                orientation=orientation,
            )
            actual = complex(
                transformed.mode(mode).coefficient_real,
                transformed.mode(mode).coefficient_imag,
            )
            assert actual == pytest.approx(expected, abs=2.0e-14)


def test_irregular_angles_do_not_force_alternation_into_pure_physical_m3():
    values = np.asarray([1.0, 2.0, 1.0, 2.0, 1.0, 2.0])
    angles = np.asarray([0.0, 0.71, 1.88, 3.02, 4.19, 5.41])
    fit = fit_physical_angle_harmonics(
        values,
        angles,
        np.ones(6),
        np.ones(6),
        sequence_name="alternating",
        modes=(3,),
        weighting_measure="equal_atom",
        angular_radius_tolerance=1.0e-8,
        maximum_condition_number=1.0e8,
        regularization=0.0,
        phase_amplitude_tolerance=1.0e-10,
        normalization_scale=1.5,
    )
    assert fit.status is HarmonicFitStatus.RESOLVED
    assert fit.design_rank == 3
    assert fit.residual_rms is not None and fit.residual_rms > 1.0e-2


def test_underdetermined_actual_angle_mode_set_fails_closed():
    angles = np.linspace(0.0, 2.0 * math.pi, 6, endpoint=False)
    fit = fit_physical_angle_harmonics(
        [1, 2, 1, 2, 1, 2],
        angles,
        np.ones(6),
        np.ones(6),
        sequence_name="too_many_modes",
        modes=(1, 2, 3),
        weighting_measure="equal_atom",
        angular_radius_tolerance=1.0e-8,
        maximum_condition_number=1.0e12,
        regularization=0.0,
        phase_amplitude_tolerance=1.0e-10,
        normalization_scale=1.5,
    )
    assert fit.status is HarmonicFitStatus.RANK_DEFICIENT
    assert fit.design_rank < fit.parameter_count == 7
    assert fit.modes == ()


def test_singular_projected_atom_makes_physical_angle_fit_unresolved():
    fit = fit_physical_angle_harmonics(
        [1, 2, 3, 4, 5, 6],
        np.linspace(0.0, 2.0 * math.pi, 6, endpoint=False),
        np.ones(6),
        [1, 1, 0, 1, 1, 1],
        sequence_name="singular",
        modes=(1, 2),
        weighting_measure="equal_atom",
        angular_radius_tolerance=1.0e-8,
        maximum_condition_number=1.0e10,
        regularization=0.0,
        phase_amplitude_tolerance=1.0e-10,
        normalization_scale=3.5,
    )
    assert fit.status is HarmonicFitStatus.ANGULAR_COORDINATE_UNDEFINED
    assert not fit.angular_coordinate_defined
    assert fit.modes == ()


def test_boundary_measure_moment_is_not_mislabeled_as_unweighted_dft():
    values = np.asarray([1.0, 2.0, 1.0, 2.0, 1.0, 2.0])
    angles = np.asarray([0.0, 0.7, 1.9, 3.0, 4.2, 5.4])
    weights = np.asarray([1.0, 2.0, 1.2, 0.7, 1.8, 0.9])
    dft = compute_unweighted_cyclic_index_spectrum(
        values,
        sequence_name="alternating",
        cyclic_origin_atom=_origin(),
    )
    moments = compute_boundary_measure_angular_moments(
        values,
        angles,
        weights,
        sequence_name="alternating",
        modes=(3,),
        normalization_scale=1.5,
        phase_amplitude_tolerance=1.0e-10,
    )
    assert moments.weighting_measure == "arc_length_voronoi"
    assert moments.modes[0].mode == 3
    assert moments.modes[0].amplitude != pytest.approx(dft.mode(3).amplitude)


def test_zero_amplitude_has_no_continuous_phase():
    spectrum = compute_unweighted_cyclic_index_spectrum(
        np.ones(6),
        sequence_name="constant",
        cyclic_origin_atom=_origin(),
    )
    for mode in spectrum.modes[1:3]:
        assert not mode.phase_defined
        assert mode.phase is None
        assert mode.phase_uncertainty is None


def _rotate_rows(values, rotation):
    return tuple(tuple(float(x) for x in np.asarray(value) @ rotation.T) for value in values)


def _mapped_catalog(reference, *, rotations=(np.eye(3),)):
    frames = []
    for frame_index, rotation in enumerate(rotations):
        rings = []
        for source in reference.rings:
            if not source.resolved:
                rings.append(
                    FrameRingGeometry(
                        window_index=source.window_index,
                        face_index=source.face_index,
                        primitive_ring_id=source.primitive_ring_id,
                        ring_size=source.ring_size,
                        status=FrameRingGeometryStatus.REFERENCE_UNRESOLVED,
                        message=source.message,
                    )
                )
                continue
            side_frames = tuple(
                RingSideFrame(
                    side=side.side,
                    center=tuple(float(x) for x in np.asarray(side.center) @ rotation.T),
                    inward_unit_normal=tuple(float(x) for x in np.asarray(side.inward_unit_normal) @ rotation.T),
                    axis_u=tuple(float(x) for x in np.asarray(side.axis_u) @ rotation.T),
                    axis_v=tuple(float(x) for x in np.asarray(side.axis_v) @ rotation.T),
                )
                for side in source.side_frames
            )
            rings.append(
                FrameRingGeometry(
                    window_index=source.window_index,
                    face_index=source.face_index,
                    primitive_ring_id=source.primitive_ring_id,
                    ring_size=source.ring_size,
                    status=FrameRingGeometryStatus.MAPPED,
                    message="synthetic replay",
                    t_fractional_vertices=source.t_fractional_vertices,
                    t_cartesian_vertices=_rotate_rows(source.t_cartesian_vertices, rotation),
                    o_fractional_vertices=source.o_fractional_vertices,
                    o_cartesian_vertices=_rotate_rows(source.o_cartesian_vertices, rotation),
                    oxygen_vertex_centroid=tuple(float(x) for x in np.asarray(source.oxygen_vertex_centroid) @ rotation.T),
                    oxygen_area_centroid=tuple(float(x) for x in np.asarray(source.oxygen_area_centroid) @ rotation.T),
                    oxygen_area_centroid_fractional=source.oxygen_area_centroid_fractional,
                    ordered_unit_normal=tuple(float(x) for x in np.asarray(source.ordered_unit_normal) @ rotation.T),
                    side_frames=side_frames,
                    covariance_eigenvalues=source.covariance_eigenvalues,
                    vector_area_magnitude=source.vector_area_magnitude,
                    projected_area=source.projected_area,
                    perimeter=source.perimeter,
                    planarity_rms=source.planarity_rms,
                    planarity_max=source.planarity_max,
                    puckering_amplitude=source.puckering_amplitude,
                    ellipticity=source.ellipticity,
                    center_aperture_radius=source.center_aperture_radius,
                    t_o_distances=source.t_o_distances,
                    o_t_distances=source.o_t_distances,
                    center_translation_cartesian=(0.0, 0.0, 0.0),
                    center_translation_fractional=(0.0, 0.0, 0.0),
                    reference_normal_dot=1.0,
                    tilt_angle_radians=0.0,
                    in_plane_rotation_radians=0.0,
                )
            )
        frames.append(
            MappedRingGeometryFrame(
                result_position=frame_index,
                collection_frame_index=frame_index,
                frame_id=frame_index,
                step=None,
                time=None,
                status=MappedRingFrameStatus.MAPPED,
                upstream_tiling_status=FrameTilingGeometryStatus.MAPPED,
                connectivity_state_digest=reference.connectivity_state_digest,
                global_image_shift=(0, 0, 0),
                rings=tuple(rings),
            )
        )
    return FrameRingGeometryCatalog(
        reference_ring_geometry_digest=reference.digest,
        frame_tiling_geometry_digest="1" * 64,
        collection_geometry_digest="2" * 64,
        connectivity_binding_digest="3" * 64,
        options=FrameRingGeometryOptions(),
        resources=FrameRingGeometryResources(),
        frames=tuple(frames),
    )


@pytest.fixture(scope="module")
def lta_boundary_catalog():
    _topology, _tiling, _geometry, collection, _connectivity, reference = lta_reference_ring_geometry_fixture()
    mapped = _mapped_catalog(reference)
    return collection, reference, mapped, build_structural_ring_boundary_catalog(reference, mapped, collection)


def test_real_lta_reference_and_frame_boundaries_retain_all_ring_atoms(lta_boundary_catalog):
    collection, reference, mapped, catalog = lta_boundary_catalog
    assert len(catalog.reference_boundaries) == 58
    assert len(catalog.frames) == 1
    assert all(boundary.status.value == "resolved" for boundary in catalog.reference_boundaries)
    for source, boundary in zip(reference.rings, catalog.reference_boundaries, strict=True):
        assert tuple(atom.atom_ref for atom in boundary.t_atoms) == source.t_atom_refs
        assert tuple(atom.atom_ref for atom in boundary.o_atoms) == source.o_atom_refs
        assert all(atom.element in {"Si", "Al"} for atom in boundary.t_atoms)
        assert all(atom.element == "O" for atom in boundary.o_atoms)
        assert all(atom.oxygen_environment_signature for atom in boundary.o_atoms)
        assert boundary.center_kind == "oxygen_area_centroid"
        assert boundary.center_uncertainty == 0.0
    assert catalog.frame_ring_geometry_digest == mapped.digest
    assert catalog.collection_chemistry_digest


def test_rigid_rotation_preserves_local_sequences_and_harmonic_amplitudes(lta_boundary_catalog):
    collection, reference, _mapped, _catalog = lta_boundary_catalog
    angle = 0.31
    rotation = np.asarray(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    mapped = _mapped_catalog(reference, rotations=(np.eye(3), rotation))
    catalog = build_structural_ring_boundary_catalog(reference, mapped, collection)
    first, second = catalog.frames
    for before, after in zip(first.boundaries, second.boundaries, strict=True):
        np.testing.assert_allclose(
            [atom.local_coordinates for atom in before.o_atoms],
            [atom.local_coordinates for atom in after.o_atoms],
            atol=3.0e-9,
        )
        for left, right in zip(before.cyclic_spectra, after.cyclic_spectra, strict=True):
            np.testing.assert_allclose(
                [mode.amplitude for mode in left.modes],
                [mode.amplitude for mode in right.modes],
                atol=3.0e-9,
            )

def test_source_bound_optional_lta_alias_is_attached_only_after_validation(lta_boundary_catalog):
    collection, reference, mapped, _catalog = lta_boundary_catalog
    atom_index = reference.rings[0].o_atom_refs[0].atom_index
    profile = LtaOxygenAliasProfile(
        profile_id="partial-audit-profile",
        reference_ring_geometry_digest=reference.digest,
        oxygen_aliases=((atom_index, "O(2)"),),
        require_complete=False,
    )
    catalog = build_structural_ring_boundary_catalog(
        reference, mapped, collection, alias_profile=profile
    )
    assert catalog.alias_validation_status.value == "validated"
    attached = [
        atom.crystallographic_alias
        for boundary in catalog.reference_boundaries
        for atom in boundary.o_atoms
        if atom.atom_ref.atom_index == atom_index
    ]
    assert attached and set(attached) == {"O(2)"}


def test_alias_profiles_fail_closed_on_source_mismatch_and_incomplete_mapping(lta_boundary_catalog):
    collection, reference, mapped, _catalog = lta_boundary_catalog
    mismatch = LtaOxygenAliasProfile(
        profile_id="bad-source",
        reference_ring_geometry_digest="0" * 64,
        oxygen_aliases=(),
        require_complete=False,
    )
    with pytest.raises(RingBoundaryAliasError, match="different reference"):
        build_structural_ring_boundary_catalog(reference, mapped, collection, alias_profile=mismatch)

    incomplete = LtaOxygenAliasProfile(
        profile_id="incomplete",
        reference_ring_geometry_digest=reference.digest,
        oxygen_aliases=(),
        require_complete=True,
    )
    with pytest.raises(RingBoundaryAliasError, match="missing"):
        build_structural_ring_boundary_catalog(reference, mapped, collection, alias_profile=incomplete)


def test_serialization_replay_resource_preflight_and_public_exports(lta_boundary_catalog):
    collection, reference, mapped, catalog = lta_boundary_catalog
    rebuilt = StructuralRingBoundaryCatalog.from_dict(
        catalog.to_dict(),
        reference_geometry=reference,
        frame_geometry=mapped,
        collection=collection,
    )
    assert rebuilt == catalog
    payload = deepcopy(catalog.to_dict())
    payload["reference_boundaries"][0]["center_coordinates"][0] += 0.1
    with pytest.raises(analysis.RingBoundarySerializationError):
        StructuralRingBoundaryCatalog.from_dict(
            payload,
            reference_geometry=reference,
            frame_geometry=mapped,
            collection=collection,
        )
    with pytest.raises(RingBoundaryResourceError, match="max_rings"):
        build_structural_ring_boundary_catalog(
            reference,
            mapped,
            collection,
            resources=RingBoundaryResources(max_rings=1),
        )
    assert analysis.build_structural_ring_boundary_catalog is build_structural_ring_boundary_catalog
    assert mdstats.StructuralRingBoundaryCatalog is StructuralRingBoundaryCatalog
    assert "StructuralRingBoundaryCatalog" in analysis.__all__
