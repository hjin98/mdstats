from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from mdstats.io import (
    EnsembleKind,
    InferenceStatus,
    SimulationControlCertificate,
    certify_vasp_simulation_controls,
    read_vasp_run_controls,
)


def _control_xml(*, mdalgo=2, smass=-3.0, isif=2, extra="", system="wrong NVT label") -> str:
    return f'''<?xml version="1.0"?>
<modeling>
  <generator><i name="program" type="string">vasp</i><i name="version" type="string">6.4.2</i></generator>
  <incar><i name="SYSTEM" type="string">{system}</i><i name="IBRION" type="int">0</i>
    <i name="MDALGO" type="int">{mdalgo}</i><i name="SMASS">{smass}</i><i name="ISIF" type="int">{isif}</i>{extra}
  </incar>
  <kpoints><varray name="kpointlist"><v>0 0 0</v></varray><varray name="weights"><v>1</v></varray></kpoints>
  <parameters><separator name="ionic"><i name="IBRION" type="int">0</i>
    <i name="NSW" type="int">1</i><i name="POTIM">1.0</i><i name="MDALGO" type="int">{mdalgo}</i>
    <i name="SMASS">{smass}</i><i name="ISIF" type="int">{isif}</i>{extra}
  </separator><separator name="electronic"><i name="EDIFF">1e-6</i><i name="NELM" type="int">100</i></separator></parameters>
  <atominfo><atoms>1</atoms><types>1</types>
    <array name="atoms"><set><rc><c>Na</c><c>1</c></rc></set></array>
    <array name="atomtypes"><set><rc><c>1</c><c>Na</c><c>22.99</c><c>1</c><c>PAW</c></rc></set></array>
  </atominfo>
  <structure name="initialpos"><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal><varray name="positions"><v>0 0 0</v></varray></structure>
  <calculation><scstep><energy><i name="e_fr_energy">-10</i><i name="e_0_energy">-10</i></energy></scstep>
    <structure><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
      <varray name="positions"><v>0 0 0</v></varray></structure>
    <varray name="forces"><v>0.1 0 0</v></varray>
    <varray name="stress"><v>0 0 0</v><v>0 0 0</v><v>0 0 0</v></varray>
    <energy><i name="e_fr_energy">-10</i><i name="e_0_energy">-10</i><i name="e_wo_entrp">-10</i><i name="kinetic">0.5</i><i name="nosepot">0</i>
      <i name="nosekinetic">0</i><i name="lattice kinetic">0</i><i name="total">-9.5</i></energy>
  </calculation>
</modeling>'''


def _write(tmp_path: Path, **kwargs) -> Path:
    path = tmp_path / "vasprun.xml"
    path.write_text(_control_xml(**kwargs), encoding="utf-8")
    return path


def test_ens1_nose_smass_minus_three_resolves_fixed_cell_nve_and_ignores_system(tmp_path: Path):
    path = _write(tmp_path)
    result = certify_vasp_simulation_controls(path)

    assert result.dynamics_status is InferenceStatus.RESOLVED
    assert result.dynamics_mode == "molecular_dynamics"
    assert result.ensemble_status is InferenceStatus.RESOLVED
    assert result.ensemble is EnsembleKind.NVE
    assert result.propagator.kind == "nose_hoover_family"
    assert result.thermostat.kind == "none"
    assert result.thermostat.active is False
    assert result.thermostat.parameter("friction") == "not_applicable"
    assert result.cell_control.kind == "fixed_cell"
    assert result.barostat.kind == "none"
    assert result.bias.status is InferenceStatus.UNRESOLVED
    assert result.constraints.status is InferenceStatus.UNRESOLVED
    assert result.force_provenance.kind == "vasp_dft_hellmann_feynman"
    assert result.initial_velocity_provenance.kind == "nonzero_initial_kinetic_energy_source_unknown"
    assert all("SYSTEM" not in item.outcome for item in result.decisions)
    assert result.ensemble_dependent_methods_permitted


def test_ens1_langevin_fixed_cell_nvt_and_variable_cell_npt_nph(tmp_path: Path):
    nvt = certify_vasp_simulation_controls(
        _write(tmp_path, mdalgo=3, smass=-3, isif=2, extra='<v name="LANGEVIN_GAMMA">10 20</v>')
    )
    assert nvt.ensemble is EnsembleKind.NVT
    assert nvt.thermostat.kind == "langevin"
    assert nvt.thermostat.parameter("friction_ps^-1") == (10.0, 20.0)

    path_npt = tmp_path / "npt.xml"
    path_npt.write_text(
        _control_xml(mdalgo=3, smass=-3, isif=3, extra='<v name="LANGEVIN_GAMMA">10 20</v><i name="LANGEVIN_GAMMA_L">5</i><i name="PMASS">1000</i>'),
        encoding="utf-8",
    )
    npt = certify_vasp_simulation_controls(path_npt)
    assert npt.ensemble is EnsembleKind.NPT
    assert npt.barostat.kind == "parrinello_rahman"

    path_nph = tmp_path / "nph.xml"
    path_nph.write_text(
        _control_xml(mdalgo=3, smass=-3, isif=3, extra='<v name="LANGEVIN_GAMMA">0 0</v><i name="LANGEVIN_GAMMA_L">0</i><i name="PMASS">1000</i>'),
        encoding="utf-8",
    )
    nph = certify_vasp_simulation_controls(path_nph)
    assert nph.ensemble is EnsembleKind.NPH
    assert nph.thermostat.active is False


def test_ens1_smass_driven_modes_are_not_mislabeled_as_equilibrium(tmp_path: Path):
    ramp = certify_vasp_simulation_controls(_write(tmp_path, smass=-1))
    assert ramp.ensemble is EnsembleKind.TEMPERATURE_RAMP
    assert ramp.dynamics_mode == "velocity_rescaled_temperature_schedule"
    assert ramp.thermostat.kind == "deterministic_velocity_rescaling"

    path = tmp_path / "constant.xml"
    path.write_text(_control_xml(smass=-2), encoding="utf-8")
    constant = certify_vasp_simulation_controls(path)
    assert constant.ensemble is EnsembleKind.CONSTANT_VELOCITY_PATH
    assert constant.dynamics_mode == "constant_velocity_path"


def test_ens1_bound_iconst_resolves_constraint_and_bias_status(tmp_path: Path):
    path = _write(tmp_path)
    iconst = tmp_path / "ICONST"
    iconst.write_text("R 1 2 0\nR 1 2 5\nR 1 2 8\n", encoding="utf-8")
    result = certify_vasp_simulation_controls(
        path, companion_files={"constraint_definition": iconst}
    )
    assert result.constraints.status is InferenceStatus.RESOLVED
    assert result.constraints.active is True
    assert result.bias.status is InferenceStatus.RESOLVED
    assert result.bias.active is True
    assert result.bias.parameter("iconst_bias_statuses") == (5, 8)



def test_ens1_andersen_probability_resolves_nve_and_nvt(tmp_path: Path):
    nve = certify_vasp_simulation_controls(
        _write(tmp_path, mdalgo=1, extra='<i name="ANDERSEN_PROB">0</i>')
    )
    assert nve.ensemble is EnsembleKind.NVE
    assert nve.thermostat.active is False

    path = tmp_path / "andersen_nvt.xml"
    path.write_text(
        _control_xml(mdalgo=1, extra='<i name="ANDERSEN_PROB">0.2</i>'),
        encoding="utf-8",
    )
    nvt = certify_vasp_simulation_controls(path)
    assert nvt.ensemble is EnsembleKind.NVT
    assert nvt.thermostat.kind == "andersen"
    assert nvt.thermostat.parameter("ANDERSEN_PROB") == pytest.approx(0.2)


def test_ens1_missing_required_thermostat_controls_stays_unresolved(tmp_path: Path):
    path = _write(tmp_path, mdalgo=4)
    result = certify_vasp_simulation_controls(path)
    assert result.ensemble_status is InferenceStatus.UNRESOLVED
    assert result.ensemble is EnsembleKind.UNKNOWN
    assert not result.ensemble_dependent_methods_permitted
    assert any("chain controls" in reason for reason in result.unresolved_reasons)


def test_ens1_round_trip_rejects_tampering(tmp_path: Path):
    result = certify_vasp_simulation_controls(_write(tmp_path))
    assert SimulationControlCertificate.from_dict(result.to_dict()) == result
    payload = result.to_dict()
    payload["ensemble"] = "NVT"
    with pytest.raises(ValueError, match="signature"):
        SimulationControlCertificate.from_dict(payload)


def test_vasp_frame_reader_attaches_ens1_metadata(tmp_path: Path):
    trajectory = mdstats.read_vasp_frames(str(_write(tmp_path)))
    payload = trajectory.metadata["simulation_control_certificate"]
    certificate = SimulationControlCertificate.from_dict(payload)
    assert certificate.ensemble is EnsembleKind.NVE
    assert trajectory.metadata["simulation_control_certificate_signature"] == certificate.signature
    quality_payload = trajectory.metadata["trajectory_quality_verdict"]
    assert quality_payload["schema"] == "mdstats.trajectory-quality-verdict.v1"
    assert trajectory.metadata["trajectory_quality_verdict_signature"] == quality_payload["signature"]
    admissibility_payload = trajectory.metadata["pmf_admissibility_certificate"]
    admissibility = mdstats.PmfAdmissibilityCertificate.from_dict(
        admissibility_payload
    )
    assert (
        trajectory.metadata["pmf_admissibility_certificate_signature"]
        == admissibility.signature
    )


def test_ens1_accepts_prebuilt_ens0_bundle_and_public_exports(tmp_path: Path):
    bundle = read_vasp_run_controls(_write(tmp_path))
    result = certify_vasp_simulation_controls(bundle)
    assert result.source_control_bundle_signature == bundle.signature
    assert mdstats.certify_vasp_simulation_controls is certify_vasp_simulation_controls
    assert "SimulationControlCertificate" in mdstats.__all__


def test_vasp_stat2_convenience_and_subselection_contract(tmp_path: Path):
    path = _write(tmp_path)
    result = mdstats.assess_vasp_pmf_admissibility(path)
    assert result.ensemble is EnsembleKind.NVE
    assert result.regime_admissibility

    segment = mdstats.read_vasp_frames(str(path), stop=1)
    assert (
        segment.metadata["pmf_admissibility_assessment_status"]
        == "not_evaluated_for_subselected_source_segment"
    )
    assert "pmf_admissibility_certificate" not in segment.metadata
