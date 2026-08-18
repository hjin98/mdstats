from __future__ import annotations

import numpy as np
import pytest

import mdstats
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    BoxOriginFrame,
    CellHandednessError,
    EvidenceState,
    ForceFrame,
    ForceSourceProvenance,
    GeometricForceTransformStatus,
    LatticeBasisContinuityError,
    LatticeGaugeFrameStatus,
    LatticeGaugeOptions,
    PMFForceAdmissibilityStatus,
    PositionFrame,
    ReferenceCellDefinition,
    ReferenceCellError,
    SourceCoordinateContract,
    SourceFieldSemantics,
    SourceSemanticsError,
    UnsupportedBasisChangeError,
    VelocityFrame,
    build_periodic_lattice_gauge,
    infer_source_field_semantics,
    prepare_source_coordinate_contract,
    reference_cell_from_source_frame,
)
from mdstats.io.common import RawFrameCollection
from mdstats.preprocess.normalize import normalize_raw_frame_collection
from mdstats.provenance import FrameCollectionProvenance


def _collection(
    cells: np.ndarray,
    *,
    pbc=(True, True, True),
    forces: bool = True,
    metadata: dict | None = None,
) -> AtomisticFrameCollection:
    cells = np.asarray(cells, dtype=np.float64)
    n_frames = cells.shape[0]
    fractional = np.zeros((n_frames, 2, 3), dtype=np.float64)
    fractional[:, 1] = np.array([0.25, 0.5, 0.75])
    velocities = np.zeros_like(fractional)
    force_values = np.ones_like(fractional) if forces else None
    return AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.array([11, 8], dtype=np.int32),
        masses=np.array([22.98976928, 15.999], dtype=np.float64),
        pbc=np.asarray(pbc, dtype=np.bool_),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64),
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=velocities,
        forces=force_values,
        provenance=FrameCollectionProvenance(
            source_format="ase-structure-collection",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="internal",
        ),
        metadata=dict(metadata or {}),
    )


def _base_cell() -> np.ndarray:
    return np.array(
        [[4.0, 0.0, 0.0], [0.7, 5.0, 0.0], [0.2, 0.4, 6.0]],
        dtype=np.float64,
    )


def test_infers_normalized_source_field_semantics_without_overclaiming_pmf():
    collection = _collection(np.repeat(_base_cell()[None, :, :], 2, axis=0))
    semantics = infer_source_field_semantics(collection)
    assert semantics.position_frame is PositionFrame.CELL_ORIGIN_RELATIVE_CARTESIAN
    assert semantics.velocity_frame is VelocityFrame.NORMALIZED_CARTESIAN
    assert semantics.force_frame is ForceFrame.NORMALIZED_CARTESIAN_COVECTOR
    assert semantics.box_origin_frame is BoxOriginFrame.ZERO_ORIGIN_CONVENTION

    contract = prepare_source_coordinate_contract(collection)
    assert (
        contract.force_admissibility.geometric_status
        is GeometricForceTransformStatus.EXACT_EXTERNAL_AFFINE_COVECTOR
    )
    assert (
        contract.force_admissibility.pmf_status
        is PMFForceAdmissibilityStatus.PMF_FORCE_PROVENANCE_UNKNOWN
    )
    assert contract.signature == prepare_source_coordinate_contract(collection).signature


def test_unknown_velocity_semantics_blocks_only_velocity_dependent_claim():
    collection = _collection(np.repeat(_base_cell()[None, :, :], 2, axis=0))
    semantics = SourceFieldSemantics(
        position_frame=PositionFrame.CELL_ORIGIN_RELATIVE_CARTESIAN,
        velocity_frame=VelocityFrame.UNKNOWN,
        force_frame=ForceFrame.NORMALIZED_CARTESIAN_COVECTOR,
        box_origin_frame=BoxOriginFrame.ZERO_ORIGIN_CONVENTION,
    )
    contract = prepare_source_coordinate_contract(collection, semantics=semantics)
    contract.semantics.require_positions("density")
    contract.semantics.require_forces("geometric force transform")
    with pytest.raises(SourceSemanticsError, match="velocities"):
        contract.semantics.require_velocities("registered VACF")



def test_normalization_persists_canonical_source_field_semantics():
    cells = np.repeat(_base_cell()[None, :, :], 2, axis=0)
    fractional = np.zeros((2, 2, 3), dtype=np.float64)
    fractional[:, 1] = np.array([0.25, 0.5, 0.75])
    raw = RawFrameCollection(
        source_ids=None,
        source_type_ids=None,
        atomic_numbers=np.repeat(
            np.array([[11, 8]], dtype=np.int32), 2, axis=0
        ),
        masses=np.repeat(
            np.array([[22.98976928, 15.999]], dtype=np.float64), 2, axis=0
        ),
        frame_ids=np.arange(2, dtype=np.int64),
        steps=np.arange(2, dtype=np.int64),
        times=np.arange(2, dtype=np.float64),
        cells=cells,
        origins=np.zeros((2, 3), dtype=np.float64),
        pbc=np.ones(3, dtype=np.bool_),
        coordinate_kind="unwrapped_fractional",
        coordinates=fractional,
        velocities=np.zeros_like(fractional),
        forces=np.ones_like(fractional),
    )
    normalized = normalize_raw_frame_collection(
        raw,
        frame_semantics="trajectory",
        source_format="ase-structure-collection",
        source_files=("synthetic",),
        units_source="internal",
        stress_source=None,
    )
    assert normalized.metadata["source_field_semantics"] == {
        "schema": "mdstats.source-field-semantics.v1",
        "position_frame": "cell_origin_relative_cartesian",
        "velocity_frame": "normalized_cartesian",
        "force_frame": "normalized_cartesian_covector",
        "box_origin_frame": "zero_origin_convention",
    }


def test_lattice_gauge_uses_temporal_and_ensemble_comparison_anchors():
    base = _base_cell()
    cells = np.stack([base, 1.05 * base, 1.10 * base])

    trajectory = _collection(cells)
    trajectory_gauge = build_periodic_lattice_gauge(trajectory)
    assert [frame.comparison_frame_index for frame in trajectory_gauge.frames] == [
        0,
        0,
        1,
    ]
    assert all(
        frame.status is LatticeGaugeFrameStatus.CONTINUOUS_REPORTED_BASIS
        for frame in trajectory_gauge.frames[1:]
    )

    ensemble = trajectory.as_ensemble()
    ensemble_gauge = build_periodic_lattice_gauge(ensemble)
    assert [frame.comparison_frame_index for frame in ensemble_gauge.frames] == [
        0,
        0,
        0,
    ]


def test_unimodular_basis_relabel_is_rejected_by_default_and_explicitly_reconciled():
    first = _base_cell()
    physical_second = first @ np.diag([1.002, 0.999, 1.001])
    relabel = np.array([[1, 1, 0], [0, 1, 0], [0, 0, 1]], dtype=np.int64)
    reported_second = relabel @ physical_second
    collection = _collection(np.stack([first, reported_second]))

    with pytest.raises(UnsupportedBasisChangeError, match="unimodular"):
        build_periodic_lattice_gauge(collection)

    gauge = build_periodic_lattice_gauge(
        collection,
        options=LatticeGaugeOptions(reconcile_unimodular=True),
    )
    assert gauge.reconciled_frame_count == 1
    assert (
        gauge.frames[1].status
        is LatticeGaugeFrameStatus.RECONCILED_UNIMODULAR_BASIS
    )
    expected_inverse = np.linalg.inv(relabel).astype(np.int64)
    np.testing.assert_array_equal(gauge.gauge_matrix(1), expected_inverse)
    np.testing.assert_allclose(gauge.gauged_cell(1), physical_second, atol=1.0e-12)


def test_orientation_reversing_basis_relabel_can_be_reconciled_without_silent_strain():
    first = _base_cell()
    relabel = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.int64)
    collection = _collection(np.stack([first, relabel @ first]))
    with pytest.raises(UnsupportedBasisChangeError):
        build_periodic_lattice_gauge(collection)
    gauge = build_periodic_lattice_gauge(
        collection,
        options=LatticeGaugeOptions(reconcile_unimodular=True),
    )
    np.testing.assert_allclose(gauge.gauged_cell(1), first, atol=1.0e-12)
    assert gauge.handedness == 1


def test_unresolved_abrupt_noninteger_cell_change_fails_closed():
    first = _base_cell()
    second = np.array(
        [[7.1, 0.3, 0.2], [0.4, 2.9, 1.7], [1.2, 0.5, 8.4]],
        dtype=np.float64,
    )
    collection = _collection(np.stack([first, second]))
    with pytest.raises(LatticeBasisContinuityError, match="unresolved"):
        build_periodic_lattice_gauge(
            collection,
            options=LatticeGaugeOptions(reconcile_unimodular=True),
        )


def test_handedness_change_without_lattice_equivalence_fails_closed():
    first = _base_cell()
    second = first.copy()
    second[0] *= -1.2
    second[1] += np.array([0.2, 0.3, 0.1])
    collection = _collection(np.stack([first, second]))
    with pytest.raises(CellHandednessError):
        build_periodic_lattice_gauge(
            collection,
            options=LatticeGaugeOptions(reconcile_unimodular=True),
        )


def test_selected_and_explicit_reference_cells_are_immutable_and_full_periodic():
    cells = np.stack([_base_cell(), _base_cell() * 1.01])
    collection = _collection(cells)
    gauge = build_periodic_lattice_gauge(collection)
    selected = reference_cell_from_source_frame(collection, gauge, frame_index=1)
    assert selected.source_kind == "selected_source_frame"
    assert selected.selected_frame_index == 1
    np.testing.assert_allclose(np.asarray(selected.matrix), cells[1])
    assert ReferenceCellDefinition.from_dict(selected.to_dict()) == selected

    explicit = ReferenceCellDefinition.explicit_matrix(_base_cell())
    assert explicit.source_kind == "explicit_matrix"
    assert explicit.digest == ReferenceCellDefinition.from_dict(explicit.to_dict()).digest
    with pytest.raises(ReferenceCellError, match="full 3D periodicity"):
        ReferenceCellDefinition.explicit_matrix(
            _base_cell(), periodic_axes=(True, True, False)
        )


def test_reference_cell_periodicity_and_handedness_must_match_source():
    collection = _collection(
        np.repeat(_base_cell()[None, :, :], 2, axis=0),
        pbc=(True, True, False),
    )
    with pytest.raises(ReferenceCellError, match="full 3D periodicity"):
        prepare_source_coordinate_contract(collection, reference_frame_index=0)

    fully_periodic = _collection(np.repeat(_base_cell()[None, :, :], 2, axis=0))
    left_handed = ReferenceCellDefinition.explicit_matrix(
        np.diag([-4.0, 5.0, 6.0])
    )
    with pytest.raises(CellHandednessError):
        prepare_source_coordinate_contract(
            fully_periodic,
            reference_cell=left_handed,
        )


def test_pmf_force_admissibility_requires_explicit_clean_provenance():
    collection = _collection(np.repeat(_base_cell()[None, :, :], 2, axis=0))
    clean = ForceSourceProvenance(
        physical_force_complete=EvidenceState.PRESENT,
        bias_or_constraint_force=EvidenceState.ABSENT,
        stochastic_or_thermostat_force=EvidenceState.ABSENT,
    )
    contract = prepare_source_coordinate_contract(
        collection,
        force_provenance=clean,
    )
    assert contract.force_admissibility.pmf_force_admissible

    biased = ForceSourceProvenance(
        physical_force_complete=EvidenceState.PRESENT,
        bias_or_constraint_force=EvidenceState.PRESENT,
        stochastic_or_thermostat_force=EvidenceState.ABSENT,
    )
    contract = prepare_source_coordinate_contract(
        collection,
        force_provenance=biased,
    )
    assert (
        contract.force_admissibility.geometric_status
        is GeometricForceTransformStatus.EXACT_EXTERNAL_AFFINE_COVECTOR
    )
    assert (
        contract.force_admissibility.pmf_status
        is PMFForceAdmissibilityStatus.PMF_FORCE_INADMISSIBLE_UNTRACKED_BIAS_OR_CONSTRAINT
    )


def test_contract_round_trip_and_ensemble_velocity_metadata():
    metadata = {
        "source_field_semantics": {
            "schema": "mdstats.source-field-semantics.v1",
            "position_frame": "cell_origin_relative_cartesian",
            "velocity_frame": "normalized_cartesian",
            "force_frame": "normalized_cartesian_covector",
            "box_origin_frame": "zero_origin_convention",
        }
    }
    collection = _collection(
        np.repeat(_base_cell()[None, :, :], 2, axis=0), metadata=metadata
    )
    contract = prepare_source_coordinate_contract(collection, reference_frame_index=0)
    restored = SourceCoordinateContract.from_dict(contract.to_dict())
    assert restored == contract
    assert restored.signature == contract.signature

    ensemble = collection.as_ensemble()
    semantics = infer_source_field_semantics(ensemble)
    assert semantics.velocity_frame is VelocityFrame.UNAVAILABLE
    semantics.require_positions("ensemble density")
    with pytest.raises(SourceSemanticsError):
        semantics.require_velocities("ensemble VACF")


def test_public_package_exports_stage_c0a1_contracts():
    for name in (
        "SourceFieldSemantics",
        "ReferenceCellDefinition",
        "LatticeGaugeOptions",
        "PeriodicLatticeGauge",
        "SourceCoordinateContract",
        "prepare_source_coordinate_contract",
    ):
        assert hasattr(mdstats, name)
        assert name in mdstats.__all__
