from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data import (
    AssertionVerificationStatus,
    FrameData,
    FrameEligibilityPolicy,
    FrameEligibilityState,
    GeometryFingerprintPolicy,
    ReferenceCellPolicy,
    ReferenceCellRecord,
    ReferenceCellResolutionMode,
    StrainContextClass,
    TemperatureScheduleKind,
    TemperatureTargetEvidence,
    TensorStrainClass,
    TrainingDataManifest,
    TrainingDataRunSpec,
    TrainingFrameCatalog,
    build_duplicate_detection_catalog,
    build_reference_cell_catalog,
    build_temperature_condition,
    build_training_data_source_catalog,
    build_training_frame_catalog,
    compute_frame_strain,
    frame_uid,
    geometry_fingerprint,
    label_payload_digest,
    labeled_configuration_fingerprint,
    source_occurrence_signature,
)
from mdstats.training_data._common import TrainingDataSerializationError, digest


def _atominfo(elements: tuple[str, ...]) -> str:
    unique: list[str] = []
    for symbol in elements:
        if symbol not in unique:
            unique.append(symbol)
    type_index = {symbol: index + 1 for index, symbol in enumerate(unique)}
    atoms = "".join(
        f"<rc><c>{symbol}</c><c>{type_index[symbol]}</c></rc>"
        for symbol in elements
    )
    types = "".join(
        f"<rc><c>{elements.count(symbol)}</c><c>{symbol}</c><c>1.0</c><c>1</c>"
        f"<c>PAW_PBE {symbol} test</c></rc>"
        for symbol in unique
    )
    return f'''<atominfo><atoms>{len(elements)}</atoms><types>{len(unique)}</types>
      <array name="atoms"><set>{atoms}</set></array>
      <array name="atomtypes"><set>{types}</set></array>
    </atominfo>'''


def _vectors(elements: tuple[str, ...], *, value: str) -> str:
    return "".join(f"<v>{value}</v>" for _ in elements)


def _vasprun(elements: tuple[str, ...]) -> str:
    gamma = " ".join("10" for _ in sorted(set(elements)))
    calculations = []
    for index, (position, energy) in enumerate((("0 0 0", -10.0), ("0.1 0 0", -9.9))):
        calculations.append(f'''
  <calculation>
    <scstep><energy><i name="e_fr_energy">{energy}</i><i name="e_0_energy">{energy + 0.1}</i></energy></scstep>
    <structure><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
      <varray name="positions">{_vectors(elements, value=position)}</varray></structure>
    <varray name="forces">{_vectors(elements, value="0.1 0 0")}</varray>
    <varray name="stress"><v>-100 0 0</v><v>0 -100 0</v><v>0 0 -100</v></varray>
    <energy><i name="e_fr_energy">{energy}</i><i name="e_0_energy">{energy + 0.1}</i><i name="e_wo_entrp">{energy + 0.05}</i>
      <i name="kinetic">0.5</i><i name="nosepot">0</i><i name="nosekinetic">0</i>
      <i name="lattice kinetic">0</i><i name="total">{energy + 0.5}</i></energy>
  </calculation>''')
    return f'''<?xml version="1.0"?>
<modeling>
  <generator><i name="program" type="string">vasp</i><i name="version" type="string">6.4.2</i><i name="subversion" type="string">test</i></generator>
  <incar>
    <i name="IBRION" type="int">0</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i><i name="ISIF" type="int">2</i>
    <v name="LANGEVIN_GAMMA">{gamma}</v><i name="GGA" type="string">PE</i>
    <i name="ISMEAR" type="int">0</i><i name="SIGMA">0.05</i><i name="ISPIN" type="int">1</i>
    <i name="LDAU" type="logical">F</i><i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
    <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
  </incar>
  <kpoints><generation param="Gamma"><v name="divisions">1 1 1</v></generation>
    <varray name="kpointlist"><v>0 0 0</v></varray><varray name="weights"><v>1</v></varray></kpoints>
  <parameters>
    <separator name="electronic"><i name="EDIFF">1e-5</i><i name="NELM" type="int">100</i>
      <i name="NELMIN" type="int">2</i><i name="ALGO" type="string">Normal</i>
      <i name="GGA" type="string">PE</i><i name="ISMEAR" type="int">0</i><i name="SIGMA">0.05</i>
      <i name="ISPIN" type="int">1</i><i name="LDAU" type="logical">F</i>
      <i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
      <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
    </separator>
    <separator name="ionic"><i name="IBRION" type="int">0</i><i name="NSW" type="int">2</i><i name="POTIM">1</i>
      <i name="MDALGO" type="int">3</i><i name="SMASS">-3</i><i name="ISIF" type="int">2</i><i name="ISYM" type="int">0</i>
      <v name="LANGEVIN_GAMMA">{gamma}</v>
    </separator>
  </parameters>
  {_atominfo(elements)}
  <structure name="initialpos"><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
    <varray name="positions">{_vectors(elements, value="0 0 0")}</varray></structure>
  {''.join(calculations)}
</modeling>'''


def _source_catalog(tmp_path: Path):
    elements = ("Li", "O")
    runs = []
    for run_id in ("reference", "strained"):
        directory = tmp_path / run_id
        directory.mkdir()
        (directory / "vasprun.xml").write_text(_vasprun(elements), encoding="utf-8")
        runs.append(
            TrainingDataRunSpec(
                run_id=run_id,
                vasprun=f"{run_id}/vasprun.xml",
                reference_group="lta",
                reference_run_id=None if run_id == "reference" else "reference",
                assertions=(
                    ()
                    if run_id == "reference"
                    else (("intended_strain_class", "shear"), ("intended_strain_magnitude", 0.02))
                ),
            )
        )
    manifest = TrainingDataManifest(dataset_id="data3", system_profile="lta", runs=tuple(runs))
    return build_training_data_source_catalog(manifest, base_directory=tmp_path)


def _frame_data(*, shear: bool, duplicate_boundary: bool = False) -> FrameData:
    reference = np.diag([10.0, 10.0, 10.0])
    deformed = reference.copy()
    if shear:
        # ASE row-vector convention: H_t = H_0 F^T for F_xy = 0.02.
        deformed[1, 0] = 0.2
    cells = np.stack([deformed, deformed])
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]],
            [[0.1, 0.0, 0.0], [0.25, 0.25, 0.25]],
        ],
        dtype=float,
    )
    if duplicate_boundary:
        positions[0] = np.array([[0.1, 0.0, 0.0], [0.25, 0.25, 0.25]])
    return FrameData(
        source_frame_indices=np.array([0, 1]),
        frame_ids=np.array([1, 2]),
        steps=np.array([0, 1]),
        times_ps=np.array([0.0, 0.001]),
        atomic_numbers=np.array([3, 8], dtype=np.int32),
        pbc=np.array([True, True, True]),
        cells_angstrom=cells,
        fractional_positions=positions,
        energies_ev=np.array([-10.0, -9.9]),
        forces_ev_per_angstrom=np.full((2, 2, 3), 0.1),
        stresses_ev_per_angstrom3=np.zeros((2, 3, 3)),
        temperatures_kelvin=np.array([700.0, np.nan]),
        scf_iteration_limit_reached=(False, False),
    )


def test_occurrence_geometry_and_label_identities_are_distinct() -> None:
    source_a = digest({"source": "a"})
    source_b = digest({"source": "b"})
    assert frame_uid(source_a, 0) == frame_uid(source_a, 0)
    assert frame_uid(source_a, 0) != frame_uid(source_b, 0)
    copied_a = source_occurrence_signature(
        run_id="copy-a", source_locator="a/vasprun.xml", source_identity_signature=source_a
    )
    copied_b = source_occurrence_signature(
        run_id="copy-b", source_locator="b/vasprun.xml", source_identity_signature=source_a
    )
    assert copied_a != copied_b
    assert frame_uid(copied_a, 0) != frame_uid(copied_b, 0)

    cell = np.eye(3)
    numbers = np.array([3, 8])
    pbc = np.array([True, True, True])
    first = np.array([[0.0, 0.0, 0.0], [1.2, -0.1, 0.5]])
    wrapped = np.array([[1.0, 0.0, 0.0], [0.2, 0.9, 0.5]])
    geometry_a = geometry_fingerprint(numbers, pbc, cell, first)
    geometry_b = geometry_fingerprint(numbers, pbc, cell, wrapped)
    assert geometry_a == geometry_b

    derivative = digest({"derivative": "ase-stress"})
    label_a = label_payload_digest(
        label_domain_id="domain",
        selected_energy_channel="e_fr_energy",
        energy_ev=-1.0,
        forces_ev_per_angstrom=np.zeros((2, 3)),
        stress_ev_per_angstrom3=np.zeros((3, 3)),
        derivative_convention_digest=derivative,
    )
    label_b = label_payload_digest(
        label_domain_id="domain",
        selected_energy_channel="e_fr_energy",
        energy_ev=-0.9,
        forces_ev_per_angstrom=np.zeros((2, 3)),
        stress_ev_per_angstrom3=np.zeros((3, 3)),
        derivative_convention_digest=derivative,
    )
    assert label_a != label_b
    assert labeled_configuration_fingerprint(geometry_a, label_a) != labeled_configuration_fingerprint(geometry_a, label_b)


def test_temperature_conditions_distinguish_constant_ramp_and_nve() -> None:
    source = digest({"source": "temperature"})
    constant = build_temperature_condition(
        run_id="constant",
        source_identity_signature=source,
        ensemble="NVT",
        instantaneous_temperatures_kelvin=[690.0, np.nan, 710.0],
        target_start_kelvin=700.0,
        target_end_kelvin=700.0,
        target_evidence="TEBEG/TEEND",
    )
    assert constant.schedule_kind is TemperatureScheduleKind.CONSTANT
    assert constant.instantaneous_count == 2
    assert constant.instantaneous_mean_kelvin == pytest.approx(700.0)
    ramp = build_temperature_condition(
        run_id="ramp",
        source_identity_signature=source,
        ensemble="NVT",
        instantaneous_temperatures_kelvin=None,
        target_start_kelvin=300.0,
        target_end_kelvin=800.0,
    )
    assert ramp.schedule_kind is TemperatureScheduleKind.RAMP
    nve = build_temperature_condition(
        run_id="nve",
        source_identity_signature=source,
        ensemble="NVE",
        instantaneous_temperatures_kelvin=[500.0],
    )
    assert nve.schedule_kind is TemperatureScheduleKind.NOT_APPLICABLE


def test_reference_resolution_and_row_vector_strain_reconstruction(tmp_path: Path) -> None:
    catalog = _source_catalog(tmp_path)
    frame_data = {
        "reference": _frame_data(shear=False),
        "strained": _frame_data(shear=True),
    }
    result = build_training_frame_catalog(
        catalog,
        frame_data,
        temperature_targets_by_run={
            "reference": TemperatureTargetEvidence(700.0, 700.0, "test"),
            "strained": TemperatureTargetEvidence(700.0, 700.0, "test"),
        },
    )
    assert len(result.frames) == 4
    assert all(decision.state is FrameEligibilityState.ELIGIBLE for decision in result.eligibility.decisions)
    strained_records = [record for record in result.strain_records if result.frame(record.frame_uid).run_id == "strained"]
    assert {record.tensor_class for record in strained_records} == {TensorStrainClass.SHEAR}
    assert all(record.context_class is StrainContextClass.IMPOSED_OR_STATIC for record in strained_records)
    assert all(record.engineering_shear[0] == pytest.approx(0.02, rel=2e-4) for record in strained_records)
    assert all(record.assertion_status is AssertionVerificationStatus.VERIFIED for record in strained_records)
    assert result.frames[-1].instantaneous_temperature_kelvin is None

    rebuilt = TrainingFrameCatalog.from_dict(result.to_dict())
    assert rebuilt == result
    damaged = deepcopy(result.to_dict())
    damaged["notes"] = ["tampered"]
    with pytest.raises(TrainingDataSerializationError, match="digest mismatch"):
        TrainingFrameCatalog.from_dict(damaged)


def test_strain_classification_covers_hydrostatic_orthorhombic_rotation_and_unresolved() -> None:
    policy_digest = ReferenceCellPolicy().policy_digest
    reference = ReferenceCellRecord.create(
        reference_group="g",
        resolution_mode=ReferenceCellResolutionMode.EXPLICIT_CELL,
        source_run_id=None,
        source_frame_index=None,
        cell_matrix_angstrom=np.eye(3),
        policy_digest=policy_digest,
    )
    uid = frame_uid(digest({"source": "strain"}), 0)

    hydro = compute_frame_strain(
        frame_uid=uid,
        current_cell_angstrom=1.05 * np.eye(3),
        reference=reference,
        ensemble="NVT",
    )
    assert hydro.tensor_class is TensorStrainClass.HYDROSTATIC
    assert hydro.volume_ratio == pytest.approx(1.05**3)

    ortho = compute_frame_strain(
        frame_uid=uid,
        current_cell_angstrom=np.diag([1.02, 1.0 / 1.02, 1.0]),
        reference=reference,
        ensemble="NVT",
    )
    assert ortho.tensor_class is TensorStrainClass.ORTHORHOMBIC_OR_DEVIATORIC

    theta = 0.2
    rotation = np.array([[np.cos(theta), -np.sin(theta), 0.0], [np.sin(theta), np.cos(theta), 0.0], [0.0, 0.0, 1.0]])
    # With row-vector cells H_t = H_0 R^T.
    rotated = compute_frame_strain(
        frame_uid=uid,
        current_cell_angstrom=rotation.T,
        reference=reference,
        ensemble="NVT",
    )
    assert rotated.tensor_class is TensorStrainClass.UNSTRAINED
    assert rotated.rotation_angle_radians == pytest.approx(theta)

    unresolved = compute_frame_strain(
        frame_uid=uid,
        current_cell_angstrom=np.eye(3),
        reference=None,
        ensemble="NVT",
    )
    assert unresolved.tensor_class is TensorStrainClass.UNRESOLVED


def test_duplicate_catalog_detects_restart_boundary(tmp_path: Path) -> None:
    source_catalog = _source_catalog(tmp_path)
    result = build_training_frame_catalog(
        source_catalog,
        {
            "reference": _frame_data(shear=False),
            "strained": _frame_data(shear=False, duplicate_boundary=True),
        },
    )
    groups = [group for group in result.duplicates.geometry_groups if group.cross_source]
    assert groups
    assert any(group.restart_boundary_pattern for group in groups)
    assert all(len(set(group.run_ids)) == len(group.run_ids) for group in groups)


def test_nonfinite_force_is_cataloged_then_rejected(tmp_path: Path) -> None:
    source_catalog = _source_catalog(tmp_path)
    bad = _frame_data(shear=False)
    forces = np.array(bad.forces_ev_per_angstrom, copy=True)
    forces[1, 0, 0] = np.nan
    bad = FrameData(
        source_frame_indices=bad.source_frame_indices,
        frame_ids=bad.frame_ids,
        steps=bad.steps,
        times_ps=bad.times_ps,
        atomic_numbers=bad.atomic_numbers,
        pbc=bad.pbc,
        cells_angstrom=bad.cells_angstrom,
        fractional_positions=bad.fractional_positions,
        energies_ev=bad.energies_ev,
        forces_ev_per_angstrom=forces,
        stresses_ev_per_angstrom3=bad.stresses_ev_per_angstrom3,
        temperatures_kelvin=bad.temperatures_kelvin,
        scf_iteration_limit_reached=bad.scf_iteration_limit_reached,
    )
    result = build_training_frame_catalog(
        source_catalog,
        {"reference": bad, "strained": _frame_data(shear=False)},
        eligibility_policy=FrameEligibilityPolicy(),
    )
    decision = result.eligibility.for_frame(result.frames[1].frame_uid)
    assert decision.state is FrameEligibilityState.INELIGIBLE
    assert "nonfinite_forces" in decision.reason_codes


def test_ungrouped_fixed_cell_run_uses_implicit_self_reference() -> None:
    source = SimpleNamespace(
        run_id="ordinary",
        reference_group=None,
        reference_run_id=None,
        assertions=(),
    )
    cells = np.repeat(np.diag([10.0, 11.0, 12.0])[None, :, :], 3, axis=0)
    catalog = build_reference_cell_catalog((source,), cells_by_run={"ordinary": cells})
    resolution = catalog.resolution_for_run("ordinary")
    assert resolution.status.value == "resolved"
    assert resolution.mode is ReferenceCellResolutionMode.IMPLICIT_SELF_REFERENCE
    assert resolution.reference_group is None
    reference = catalog.record(resolution.reference_cell_id)
    record = compute_frame_strain(
        frame_uid=frame_uid(digest({"source": "ordinary"}), 0),
        current_cell_angstrom=cells[1],
        reference=reference,
        ensemble="NVT",
    )
    assert record.tensor_class is TensorStrainClass.UNSTRAINED


def test_ungrouped_variable_cell_run_remains_unresolved_by_default() -> None:
    source = SimpleNamespace(
        run_id="npt",
        reference_group=None,
        reference_run_id=None,
        assertions=(),
    )
    cells = np.stack((np.eye(3), 1.01 * np.eye(3)))
    catalog = build_reference_cell_catalog((source,), cells_by_run={"npt": cells})
    resolution = catalog.resolution_for_run("npt")
    assert resolution.status.value == "unresolved"
    assert "variable cells" in resolution.reasons[0]


def test_reference_catalog_fails_closed_on_ambiguous_cells() -> None:
    sources = (
        SimpleNamespace(run_id="a", reference_group="g", reference_run_id=None, assertions=()),
        SimpleNamespace(run_id="b", reference_group="g", reference_run_id=None, assertions=()),
    )
    ambiguous = build_reference_cell_catalog(
        sources,
        cells_by_run={
            "a": np.repeat(np.eye(3)[None, :, :], 2, axis=0),
            "b": np.repeat((1.01 * np.eye(3))[None, :, :], 2, axis=0),
        },
    )
    assert all(item.status.value == "unresolved" for item in ambiguous.resolutions)

    consensus = build_reference_cell_catalog(
        sources,
        cells_by_run={
            "a": np.repeat(np.eye(3)[None, :, :], 2, axis=0),
            "b": np.repeat(np.eye(3)[None, :, :], 2, axis=0),
        },
    )
    assert all(item.status.value == "resolved" for item in consensus.resolutions)


def test_strain_assertion_mismatch_is_recorded_not_hidden() -> None:
    policy_digest = ReferenceCellPolicy().policy_digest
    reference = ReferenceCellRecord.create(
        reference_group="g",
        resolution_mode=ReferenceCellResolutionMode.EXPLICIT_CELL,
        source_run_id=None,
        source_frame_index=None,
        cell_matrix_angstrom=np.eye(3),
        policy_digest=policy_digest,
    )
    record = compute_frame_strain(
        frame_uid=frame_uid(digest({"source": "assertion"}), 0),
        current_cell_angstrom=1.02 * np.eye(3),
        reference=reference,
        ensemble="NVT",
        assertions={"intended_strain_class": "shear", "intended_strain_magnitude": 0.02},
    )
    assert record.tensor_class is TensorStrainClass.HYDROSTATIC
    assert record.assertion_status is AssertionVerificationStatus.MISMATCH
    assert record.assertion_reasons


def test_reference_run_cannot_cross_reference_groups() -> None:
    sources = (
        SimpleNamespace(run_id="a", reference_group="g1", reference_run_id=None, assertions=()),
        SimpleNamespace(run_id="b", reference_group="g2", reference_run_id="a", assertions=()),
    )
    catalog = build_reference_cell_catalog(
        sources,
        cells_by_run={
            "a": np.repeat(np.eye(3)[None, :, :], 2, axis=0),
            "b": np.repeat(np.eye(3)[None, :, :], 2, axis=0),
        },
    )
    resolution = catalog.resolution_for_run("b")
    assert resolution.status.value == "unresolved"
    assert "reference_group" in resolution.reasons[0]
