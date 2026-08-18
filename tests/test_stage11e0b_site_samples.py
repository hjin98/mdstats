from __future__ import annotations

import copy
import json

import numpy as np
import pytest

import mdstats
from mdstats.analysis.site_samples import (
    EquilibriumStatus,
    FrameRegistrationGroup,
    FrameworkAlignedIonSampleCatalog,
    PMFTemperatureProvenance,
    RegistrationGroupError,
    SamplingStateProvenance,
    SegmentKind,
    SiteSampleInputError,
    StationarityStatus,
    TemporalWeightingError,
    prepare_frame_registration_group,
    prepare_framework_aligned_ion_sample_catalog,
    prepare_topology_regime_assignment,
    prepare_trajectory_segment_weighting,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    EvidenceState,
    ForceSourceProvenance,
    FrameRegistrationPolicy,
    ReferenceCellDefinition,
    RegistrationSpatialPolicy,
    prepare_frame_registration,
    prepare_source_coordinate_contract,
)
from mdstats.provenance import FrameCollectionProvenance


def _cell(scale: float = 1.0) -> np.ndarray:
    return scale * np.array(
        [[5.0, 0.0, 0.0], [0.6, 5.4, 0.0], [0.2, 0.3, 6.1]],
        dtype=np.float64,
    )


def _collection(
    *,
    frame_semantics: str = "trajectory",
    times: np.ndarray | None = None,
    cell_scale: float = 1.0,
    shift: float = 0.0,
    with_forces: bool = True,
) -> AtomisticFrameCollection:
    if times is None:
        times = np.array([0.0, 1.0, 2.0, 10.0, 11.0, 12.0])
    n_frames = len(times)
    base = np.array(
        [[0.12, 0.18, 0.24], [0.32, 0.36, 0.40], [0.62, 0.67, 0.71]],
        dtype=np.float64,
    )
    fractional = np.repeat(base[None, :, :], n_frames, axis=0)
    fractional[:, 1, 0] += np.linspace(0.0, 0.15, n_frames) + shift
    fractional[:, 2, 1] += np.linspace(0.0, 0.10, n_frames)
    forces = None
    if with_forces:
        forces = (
            np.arange(n_frames * 3 * 3, dtype=np.float64).reshape(n_frames, 3, 3)
            / 13.0
        )
    return AtomisticFrameCollection(
        frame_semantics=frame_semantics,
        frame_ids=np.arange(100, 100 + n_frames, dtype=np.int64),
        atomic_numbers=np.array([8, 11, 11], dtype=np.int32),
        masses=np.array([15.999, 22.98976928, 22.98976928]),
        pbc=np.ones(3, dtype=np.bool_),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.asarray(times, dtype=np.float64),
        cells=np.repeat(_cell(cell_scale)[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=np.zeros_like(fractional),
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


def _registration(
    collection: AtomisticFrameCollection,
    *,
    reference_material: bool = False,
):
    source = prepare_source_coordinate_contract(
        collection,
        force_provenance=ForceSourceProvenance(
            physical_force_complete=EvidenceState.PRESENT,
            bias_or_constraint_force=EvidenceState.ABSENT,
            stochastic_or_thermostat_force=EvidenceState.ABSENT,
        ),
        reference_cell=(
            ReferenceCellDefinition.explicit_matrix(_cell())
            if reference_material
            else None
        ),
    )
    policy = FrameRegistrationPolicy(
        spatial_policy=(
            RegistrationSpatialPolicy.REFERENCE_MATERIAL
            if reference_material
            else RegistrationSpatialPolicy.PHYSICAL
        ),
        require_fixed_registered_cell=True,
    )
    return prepare_frame_registration(
        collection,
        policy=policy,
        source_contract=source,
    )


def test_segment_weights_are_midpoint_time_measure_and_do_not_mix_silently():
    collection = _collection()
    registration = _registration(collection)
    with pytest.raises(TemporalWeightingError, match="explicit included_segment_ids"):
        prepare_trajectory_segment_weighting(
            collection,
            registration=registration,
            segment_start_frame_indices=(3,),
            segment_kinds=(SegmentKind.HEATING, SegmentKind.PRODUCTION),
        )
    production = prepare_trajectory_segment_weighting(
        collection,
        registration=registration,
        segment_start_frame_indices=(3,),
        segment_kinds=(SegmentKind.HEATING, SegmentKind.PRODUCTION),
        included_segment_ids=(1,),
    )
    np.testing.assert_allclose(
        production.represented_time_weights,
        np.array([0.5, 1.0, 0.5, 0.5, 1.0, 0.5]),
    )
    assert production.temporal_mask.tolist() == [False, False, False, True, True, True]
    assert production.included_represented_time == pytest.approx(2.0)
    with pytest.raises(TemporalWeightingError, match="Heating and production"):
        prepare_trajectory_segment_weighting(
            collection,
            segment_start_frame_indices=(3,),
            segment_kinds=(SegmentKind.HEATING, SegmentKind.PRODUCTION),
            included_segment_ids=(0, 1),
        )


def test_compact_species_catalog_preserves_exact_nested_subsets():
    collection = _collection()
    registration = _registration(collection)
    temporal = prepare_trajectory_segment_weighting(
        collection,
        segment_start_frame_indices=(3,),
        segment_kinds=(SegmentKind.HEATING, SegmentKind.PRODUCTION),
        included_segment_ids=(1,),
    )
    topology = prepare_topology_regime_assignment(
        collection,
        topology_regime_ids=np.array([0, 0, 0, 1, 1, 1]),
        connectivity_flicker_mask=np.array([False, False, False, False, True, False]),
    )
    position_source = np.ones((6, 2), dtype=np.bool_)
    position_source[5, 0] = False
    force_source = np.ones((6, 2), dtype=np.bool_)
    force_source[3, 1] = False
    catalog = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        species_label="Na",
        temporal_weighting=temporal,
        topology_assignment=topology,
        position_source_mask=position_source,
        force_source_mask=force_source,
    )
    assert catalog.n_samples == 12
    assert catalog.selected_atom_indices == (1, 2)
    assert catalog.evidence_masks.position_mask.sum() == 3
    assert catalog.evidence_masks.force_mask.sum() == 3
    assert catalog.evidence_masks.joint_mask.sum() == 2
    joint = catalog.evidence_view("joint")
    np.testing.assert_array_equal(
        joint.sample_indices, np.flatnonzero(catalog.evidence_masks.joint_mask)
    )
    np.testing.assert_allclose(joint.positions, catalog.registered_positions[joint.sample_indices])
    np.testing.assert_allclose(joint.forces, catalog.transformed_forces[joint.sample_indices])
    assert joint.total_ion_time == pytest.approx(1.0)
    assert np.sum(joint.normalized_weights) == pytest.approx(1.0)
    assert catalog.metadata["density_force_joint_subset_exact"] is True


def test_pmf_force_mask_requires_force_state_and_temperature_provenance():
    collection = _collection(times=np.arange(6, dtype=np.float64))
    registration = _registration(collection)
    temporal = prepare_trajectory_segment_weighting(collection)
    state = SamplingStateProvenance(
        equilibrium_status=EquilibriumStatus.DECLARED_EQUILIBRIUM,
        stationarity_status=StationarityStatus.TESTED_STATIONARY,
        declaration_source="focused test",
    )
    temperature = PMFTemperatureProvenance.declared_constant(
        600.0, source="thermostat target"
    )
    admissible = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        temporal_weighting=temporal,
        sampling_state=state,
        pmf_temperature=temperature,
    )
    np.testing.assert_array_equal(
        admissible.evidence_masks.pmf_force_mask,
        admissible.evidence_masks.joint_mask,
    )
    unknown = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        temporal_weighting=temporal,
    )
    assert not np.any(unknown.evidence_masks.pmf_force_mask)
    assert (
        admissible.force_provenance.bias_force_evidence
        is EvidenceState.ABSENT
    )


def test_structure_fitted_registration_retains_force_but_rejects_pmf_subset():
    collection = _collection(times=np.arange(6, dtype=np.float64))
    source = prepare_source_coordinate_contract(
        collection,
        force_provenance=ForceSourceProvenance(
            physical_force_complete=EvidenceState.PRESENT,
            bias_or_constraint_force=EvidenceState.ABSENT,
            stochastic_or_thermostat_force=EvidenceState.ABSENT,
        ),
    )
    registration = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(
            spatial_policy="translation_registered",
            translation_mode="matched_reference",
            reference_atom_indices=(0,),
        ),
        source_contract=source,
    )
    catalog = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        sampling_state=SamplingStateProvenance(
            equilibrium_status="declared_equilibrium",
            stationarity_status="tested_stationary",
            declaration_source="test",
        ),
        pmf_temperature=PMFTemperatureProvenance.declared_constant(
            600.0, source="test"
        ),
    )
    assert np.any(catalog.evidence_masks.force_mask)
    assert np.any(catalog.evidence_masks.joint_mask)
    assert not np.any(catalog.evidence_masks.pmf_force_mask)
    assert catalog.force_provenance.geometric_status.value == (
        "diagnostic_structure_fitted_projection"
    )
    assert catalog.force_provenance.pmf_status.value == (
        "pmf_force_inadmissible_structure_fitted_map"
    )


def test_lazy_structural_annotations_materialize_only_requested_samples():
    collection = _collection(times=np.arange(6, dtype=np.float64))
    catalog = prepare_framework_aligned_ion_sample_catalog(
        collection,
        _registration(collection),
        species_atomic_number=11,
    )
    calls: list[tuple[int, ...]] = []

    def resolver(catalog_, indices):
        assert catalog_.signature == catalog.signature
        calls.append(tuple(int(item) for item in indices))
        return {
            "nearest_ring_id": catalog_.frame_indices[indices] % 3,
            "distance": np.linalg.norm(catalog_.registered_positions[indices], axis=1),
        }

    view = catalog.structural_annotations(resolver)
    first = view.resolve(channel="joint")
    second = view.resolve(channel="joint")
    assert first is second
    assert len(calls) == 1
    assert first["nearest_ring_id"].shape == (catalog.evidence_masks.joint_mask.sum(),)
    with pytest.raises(ValueError):
        first["distance"][0] = 0.0


def test_registration_group_certifies_one_fixed_periodic_domain():
    collection_a = _collection(times=np.arange(4, dtype=np.float64))
    collection_b = _collection(times=np.arange(4, dtype=np.float64), shift=0.02)
    registration_a = _registration(collection_a)
    registration_b = _registration(collection_b)
    group = prepare_frame_registration_group(
        ((collection_a, registration_a), (collection_b, registration_b))
    )
    assert len(group.members) == 2
    assert group.member_index_for_registration(registration_b.signature) == 1
    catalog = prepare_framework_aligned_ion_sample_catalog(
        collection_b,
        registration_b,
        species_atomic_number=11,
        registration_group=group,
    )
    assert catalog.registration_group_signature == group.signature
    assert catalog.registration_group_member_index == 1
    replay = FrameRegistrationGroup.from_dict(
        json.loads(json.dumps(group.to_dict()))
    )
    assert replay.signature == group.signature

    incompatible = _collection(
        times=np.arange(4, dtype=np.float64), cell_scale=1.01
    )
    with pytest.raises(RegistrationGroupError, match="differs from the shared domain"):
        prepare_frame_registration_group(
            ((collection_a, registration_a), (incompatible, _registration(incompatible)))
        )


def test_ensemble_weighting_has_equal_measure_and_no_continuity_claim():
    trajectory = _collection(times=np.arange(4, dtype=np.float64))
    ensemble = trajectory.as_ensemble()
    weighting = prepare_trajectory_segment_weighting(ensemble)
    assert weighting.frame_semantics.value == "ensemble"
    assert np.all(weighting.segment_start_mask)
    np.testing.assert_allclose(weighting.represented_time_weights, 1.0)
    assert weighting.included_segment_ids == (0, 1, 2, 3)


def test_catalog_serialization_round_trip_and_tamper_rejection():
    collection = _collection(times=np.arange(4, dtype=np.float64))
    catalog = prepare_framework_aligned_ion_sample_catalog(
        collection,
        _registration(collection),
        species_atomic_number=11,
        sampling_state=SamplingStateProvenance(
            equilibrium_status="declared_equilibrium",
            stationarity_status="assumed_stationary",
            declaration_source="test",
        ),
        pmf_temperature=PMFTemperatureProvenance.declared_constant(
            500.0, source="test"
        ),
    )
    payload = json.loads(json.dumps(catalog.to_dict()))
    replay = FrameworkAlignedIonSampleCatalog.from_dict(payload)
    assert replay.signature == catalog.signature
    np.testing.assert_allclose(replay.registered_positions, catalog.registered_positions)
    tampered = copy.deepcopy(payload)
    tampered["registered_positions"][0][0] += 0.1
    with pytest.raises(SiteSampleInputError, match="signature"):
        FrameworkAlignedIonSampleCatalog.from_dict(tampered)


def test_catalog_rejects_registration_from_a_different_collection():
    source = _collection(times=np.arange(4, dtype=np.float64))
    registration = _registration(source)
    changed = _collection(times=np.arange(4, dtype=np.float64), shift=0.2)
    with pytest.raises(SiteSampleInputError, match="not geometrically bound"):
        prepare_framework_aligned_ion_sample_catalog(
            changed,
            registration,
            species_atomic_number=11,
        )


def test_missing_force_field_retains_position_channel_and_empty_force_channels():
    collection = _collection(times=np.arange(4, dtype=np.float64), with_forces=False)
    registration = _registration(collection)
    catalog = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
    )
    assert np.any(catalog.evidence_masks.position_mask)
    assert not np.any(catalog.evidence_masks.force_mask)
    assert not np.any(catalog.evidence_masks.joint_mask)
    assert catalog.transformed_forces is None


def test_public_exports_and_analysis_only_dependency_surface():
    expected = (
        "FrameworkAlignedIonSampleCatalog",
        "TrajectorySegmentWeighting",
        "TopologyRegimeAssignment",
        "FrameRegistrationGroup",
        "prepare_framework_aligned_ion_sample_catalog",
        "prepare_trajectory_segment_weighting",
        "prepare_topology_regime_assignment",
        "prepare_frame_registration_group",
    )
    for name in expected:
        assert getattr(mdstats, name) is getattr(mdstats.analysis, name)
        assert name in mdstats.__all__
        assert name in mdstats.analysis.__all__
