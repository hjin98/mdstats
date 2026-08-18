from __future__ import annotations

import itertools
import json

import numpy as np
import pytest

import mdstats
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    AnalysisGeometryMetric,
    ClosestImageAmbiguityError,
    EvidenceState,
    ForceSourceProvenance,
    FrameRegistrationPolicy,
    FrameRegistrationResult,
    GeometricForceTransformStatus,
    LatticeGaugeOptions,
    PMFForceAdmissibilityStatus,
    ReferenceCellDefinition,
    ReferenceWeighting,
    RegistrationFitMetric,
    RegistrationSpatialPolicy,
    RegistrationValidationError,
    TranslationMode,
    closest_periodic_image,
    prepare_frame_registration,
    prepare_source_coordinate_contract,
)
from mdstats.provenance import FrameCollectionProvenance


def _base_cell() -> np.ndarray:
    return np.array(
        [[4.0, 0.0, 0.0], [0.7, 5.0, 0.0], [0.2, 0.4, 6.0]],
        dtype=np.float64,
    )


def _collection(
    cells: np.ndarray,
    fractional_positions: np.ndarray,
    *,
    frame_semantics: str = "trajectory",
    forces: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    cells = np.asarray(cells, dtype=np.float64)
    fractional_positions = np.asarray(fractional_positions, dtype=np.float64)
    n_frames, n_atoms, _ = fractional_positions.shape
    if forces is None:
        forces = np.arange(n_frames * n_atoms * 3, dtype=np.float64).reshape(
            n_frames, n_atoms, 3
        ) / 17.0
    return AtomisticFrameCollection(
        frame_semantics=frame_semantics,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.array([14, 8, 8, 11][:n_atoms], dtype=np.int32),
        masses=np.array([28.085, 15.999, 15.999, 22.98976928][:n_atoms]),
        pbc=np.ones(3, dtype=np.bool_),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64),
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional_positions,
        velocities=np.zeros_like(fractional_positions),
        forces=forces,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="internal",
        ),
    )


def _translated_variable_cell_collection() -> tuple[AtomisticFrameCollection, np.ndarray]:
    base = _base_cell()
    cells = np.stack(
        [
            base,
            base @ np.diag([1.02, 0.99, 1.01]),
            base @ np.array([[1.01, 0.01, 0.0], [0.0, 1.03, 0.0], [0.0, 0.0, 0.98]]),
            base @ np.diag([0.99, 1.01, 1.02]),
        ]
    )
    material = np.array(
        [
            [0.10, 0.20, 0.30],
            [0.32, 0.21, 0.34],
            [0.18, 0.47, 0.38],
            [0.65, 0.72, 0.25],
        ],
        dtype=np.float64,
    )
    drift = np.array([0.0, 0.4, 0.8, 1.2], dtype=np.float64)
    fractional = np.repeat(material[None, :, :], cells.shape[0], axis=0)
    fractional[..., 0] += drift[:, None]
    fractional[:, 3, 1] += np.array([0.0, 0.02, 0.05, 0.09])
    return _collection(cells, fractional), material


def test_metric_contracts_are_distinct_and_coordinate_covariant():
    fit = RegistrationFitMetric(
        matrix=((2.0, 0.2, 0.0), (0.2, 1.5, 0.1), (0.0, 0.1, 1.1)),
        units="angstrom^-2",
        coordinate_frame="q",
        transformation_provenance="test",
    )
    analysis = AnalysisGeometryMetric.euclidean(
        units="angstrom^-2", coordinate_frame="q"
    )
    assert fit.digest != analysis.digest
    transform = np.array([[1.2, 0.1, 0.0], [0.0, 0.9, 0.2], [0.0, 0.0, 1.1]])
    displacement = np.array([0.7, -0.4, 0.2])
    transformed = fit.transformed(transform, coordinate_frame="q_prime")
    np.testing.assert_allclose(
        fit.squared_norm(displacement),
        transformed.squared_norm(displacement @ transform),
        rtol=1.0e-12,
        atol=1.0e-12,
    )
    assert RegistrationFitMetric.from_dict(fit.to_dict()) == fit


def test_certified_skew_cell_image_beats_componentwise_fractional_rounding():
    cell = np.array([[4.0, 0.0, 0.0], [3.8, 1.0, 0.0], [0.2, 0.3, 3.0]])
    displacement = np.array([1.88919618, 0.74718795, -4.19925284])
    metric = RegistrationFitMetric.euclidean(units="angstrom^-2")
    result = closest_periodic_image(displacement, cell=cell, metric=metric)
    rounded = np.rint(displacement @ np.linalg.inv(cell)).astype(np.int64)
    assert tuple(rounded) == (-1, 1, -1)
    assert result.image_shift == (0, 1, -1)
    brute = []
    for shift in itertools.product(range(-4, 5), repeat=3):
        vector = displacement - np.asarray(shift) @ cell
        brute.append((float(np.dot(vector, vector)), shift))
    brute.sort()
    assert result.image_shift == brute[0][1]
    assert result.certified


def test_closest_image_tie_is_exposed_and_can_fail_closed():
    metric = RegistrationFitMetric.euclidean(units="angstrom^-2")
    result = closest_periodic_image(
        np.array([2.0, 0.0, 0.0]),
        cell=np.diag([4.0, 5.0, 6.0]),
        metric=metric,
    )
    assert result.ambiguous
    with pytest.raises(ClosestImageAmbiguityError):
        result.require_unique("test branch")


def test_physical_registration_is_identity_with_complete_coordinate_products():
    base = _base_cell()
    fractional = np.array(
        [
            [[0.1, 0.2, 0.3], [1.2, -0.1, 0.4]],
            [[0.2, 0.3, 0.4], [1.4, -0.2, 0.6]],
        ]
    )
    collection = _collection(np.repeat(base[None, :, :], 2, axis=0), fractional)
    result = prepare_frame_registration(collection)
    np.testing.assert_allclose(result.affine_matrices, np.repeat(np.eye(3)[None, :, :], 2, axis=0))
    np.testing.assert_allclose(result.affine_translations, 0.0)
    np.testing.assert_allclose(
        result.registered_unwrapped_cartesian, collection.get_positions()
    )
    reconstructed = np.einsum(
        "tni,tij->tnj",
        result.registered_wrapped_fractional + result.registered_image_shifts,
        result.registered_cells,
    )
    np.testing.assert_allclose(reconstructed, result.registered_unwrapped_cartesian)
    assert result.maximum_force_work_error is not None
    assert result.maximum_force_work_error < 1.0e-12


def test_reference_material_registration_removes_periodic_framework_drift():
    collection, material = _translated_variable_cell_collection()
    reference = ReferenceCellDefinition.explicit_matrix(_base_cell())
    source = prepare_source_coordinate_contract(
        collection,
        reference_cell=reference,
        force_provenance=ForceSourceProvenance(
            physical_force_complete=EvidenceState.PRESENT,
            bias_or_constraint_force=EvidenceState.ABSENT,
            stochastic_or_thermostat_force=EvidenceState.ABSENT,
        ),
    )
    policy = FrameRegistrationPolicy(
        spatial_policy=RegistrationSpatialPolicy.REFERENCE_MATERIAL,
        translation_mode=TranslationMode.MATCHED_REFERENCE,
        reference_atom_indices=(0, 1, 2),
        reference_frame_index=0,
        reference_weighting=ReferenceWeighting.CENTER_OF_MASS,
        force_target_atom_indices=(3,),
        require_fixed_registered_cell=True,
    )
    result = prepare_frame_registration(
        collection,
        policy=policy,
        source_contract=source,
    )
    np.testing.assert_allclose(result.registered_cells, np.repeat(_base_cell()[None, :, :], collection.n_frames, axis=0), atol=1.0e-12)
    expected_framework = material[:3] @ _base_cell()
    np.testing.assert_allclose(
        result.registered_unwrapped_cartesian[:, :3],
        np.repeat(expected_framework[None, :, :], collection.n_frames, axis=0),
        atol=1.0e-9,
    )
    assert result.translation_branch_lift is not None
    assert result.reference_translation_gauge is not None
    assert {
        frame.solver_method for frame in result.reference_translation_gauge.frames
    } == {"certified_local_convexity"}
    assert all(
        frame.uniqueness_radius_margin is not None
        and frame.uniqueness_radius_margin > 0.0
        for frame in result.reference_translation_gauge.frames
    )
    lifted = result.translation_branch_lift.lifted_translations
    np.testing.assert_allclose(lifted[:, 0], np.array([0.0, 1.6, 3.2, 4.8]), atol=1.0e-9)
    assert np.any(result.translation_branch_lift.lattice_branches != 0)
    assert (
        result.force_admissibility.geometric_status
        is GeometricForceTransformStatus.EXACT_TRANSLATION_RELATIVE_TO_DISJOINT_REFERENCE_GROUP
    )
    assert (
        result.force_admissibility.pmf_status
        is PMFForceAdmissibilityStatus.PMF_FORCE_INADMISSIBLE_STRUCTURE_FITTED_MAP
    )


def test_segment_reset_prevents_invented_cross_restart_translation_lift():
    collection, _ = _translated_variable_cell_collection()
    policy = FrameRegistrationPolicy(
        spatial_policy="reference_material",
        translation_mode="matched_reference",
        reference_atom_indices=(0, 1, 2),
        segment_reset_frame_indices=(2,),
    )
    result = prepare_frame_registration(
        collection,
        policy=policy,
        reference_cell=ReferenceCellDefinition.explicit_matrix(_base_cell()),
    )
    assert result.translation_branch_lift is not None
    lift = result.translation_branch_lift
    assert lift.segment_start_mask.tolist() == [True, False, True, False]
    np.testing.assert_allclose(lift.lifted_translations[2, 0], -0.8, atol=1.0e-9)


def test_independent_ensemble_receives_no_temporal_branch_continuity():
    trajectory, _ = _translated_variable_cell_collection()
    ensemble = trajectory.as_ensemble()
    result = prepare_frame_registration(
        ensemble,
        policy=FrameRegistrationPolicy(
            spatial_policy="reference_material",
            translation_mode="matched_reference",
            reference_atom_indices=(0, 1, 2),
        ),
        reference_cell=ReferenceCellDefinition.explicit_matrix(_base_cell()),
    )
    assert result.translation_branch_lift is not None
    assert not result.translation_branch_lift.temporal_continuity_available
    np.testing.assert_allclose(
        result.translation_branch_lift.lifted_translations,
        result.translation_branch_lift.torus_translations,
    )


def test_fixed_domain_requirement_rejects_variable_physical_cells():
    collection, _ = _translated_variable_cell_collection()
    with pytest.raises(RegistrationValidationError, match="fixed-domain"):
        prepare_frame_registration(
            collection,
            policy=FrameRegistrationPolicy(require_fixed_registered_cell=True),
        )


def test_unimodular_source_basis_relabel_does_not_change_reference_material_positions():
    base = _base_cell()
    relabel = np.array([[1, 1, 0], [0, 1, 0], [0, 0, 1]], dtype=np.int64)
    cells = np.stack([base, relabel @ base])
    material = np.array(
        [[0.1, 0.2, 0.3], [0.3, 0.4, 0.2], [0.7, 0.1, 0.5], [0.2, 0.8, 0.6]]
    )
    fractional = np.empty((2, 4, 3), dtype=np.float64)
    fractional[0] = material
    fractional[1] = material @ np.linalg.inv(relabel)
    collection = _collection(cells, fractional)
    source = prepare_source_coordinate_contract(
        collection,
        lattice_options=LatticeGaugeOptions(reconcile_unimodular=True),
        reference_cell=ReferenceCellDefinition.explicit_matrix(base),
    )
    result = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(spatial_policy="reference_material"),
        source_contract=source,
    )
    np.testing.assert_allclose(
        result.registered_unwrapped_cartesian[0],
        result.registered_unwrapped_cartesian[1],
        atol=1.0e-12,
    )


def test_registration_round_trip_serialization_and_public_exports():
    collection, _ = _translated_variable_cell_collection()
    result = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(
            spatial_policy="reference_material",
            translation_mode="matched_reference",
            reference_atom_indices=(0, 1, 2),
        ),
        reference_cell=ReferenceCellDefinition.explicit_matrix(_base_cell()),
    )
    payload = result.to_dict()
    json.dumps(payload, allow_nan=False)
    restored = FrameRegistrationResult.from_dict(payload)
    assert restored.signature == result.signature
    assert restored.reference_translation_gauge is not None
    assert restored.reference_translation_gauge.frames[0].solver_method == (
        result.reference_translation_gauge.frames[0].solver_method
    )
    np.testing.assert_allclose(
        restored.registered_unwrapped_cartesian,
        result.registered_unwrapped_cartesian,
    )
    probe = np.array([[1.0, 2.0, -1.0], [0.2, -0.3, 0.5]])
    transformed = result.transform_positions(probe, frame_index=1)
    np.testing.assert_allclose(
        result.inverse_transform_positions(transformed, frame_index=1), probe
    )
    for name in (
        "RegistrationFitMetric",
        "AnalysisGeometryMetric",
        "closest_periodic_image",
        "FrameRegistrationPolicy",
        "FrameRegistrationResult",
        "prepare_frame_registration",
    ):
        assert hasattr(mdstats, name)
        assert name in mdstats.__all__
