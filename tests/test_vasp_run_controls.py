from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.io import (
    CompanionFileState,
    ControlAuthority,
    FrameEnergyCatalog,
    NumericalMDQualityControls,
    SimulationRunControls,
    SourceControlSerializationError,
    SourceTrajectoryBundleIdentity,
    VaspRunControls,
    VaspSourceControlBundle,
    read_vasp_run_controls,
)


def _scsteps(count: int, energy: float) -> str:
    return "".join(
        f"""
        <scstep><energy>
          <i name="e_fr_energy">{energy + 0.001 * index}</i>
          <i name="e_0_energy">{energy + 0.001 * index}</i>
        </energy></scstep>
        """
        for index in range(count)
    )


def _calculation(index: int, *, omit_nosepot: bool = False) -> str:
    energy = -10.0 + 0.1 * index
    nose = "" if omit_nosepot else '<i name="nosepot">0.0</i>'
    return f"""
  <calculation>
    {_scsteps(index + 2, energy)}
    <structure>
      <crystal><varray name="basis">
        <v>10 0 0</v><v>0 10 0</v><v>0 0 10</v>
      </varray></crystal>
      <varray name="positions"><v>{0.1 * index} 0 0</v></varray>
    </structure>
    <varray name="forces"><v>0.1 0.0 0.0</v></varray>
    <varray name="stress">
      <v>-100 0 0</v><v>0 -100 0</v><v>0 0 -100</v>
    </varray>
    <energy>
      <i name="e_fr_energy">{energy}</i>
      <i name="e_0_energy">{energy + 0.01}</i>
      <i name="e_wo_entrp">{energy + 0.02}</i>
      <i name="kinetic">0.5</i>
      {nose}
      <i name="nosekinetic">0.0</i>
      <i name="lattice kinetic">0.0</i>
      <i name="total">{energy + 0.5}</i>
    </energy>
  </calculation>
"""


def _vasprun(*, omit_second_nosepot: bool = False) -> str:
    return f"""<?xml version="1.0"?>
<modeling>
  <generator>
    <i name="program" type="string">vasp</i>
    <i name="version" type="string">6.4.2</i>
    <i name="subversion" type="string">test-build</i>
  </generator>
  <incar>
    <i name="SYSTEM" type="string">Na-LTA 300K NVT AIMD</i>
    <i name="MDALGO" type="int">2</i>
    <i name="SMASS">-3.0</i>
    <i name="ISIF" type="int">2</i>
    <i name="PREC" type="string">Accurate</i>
    <i name="LREAL" type="string">Auto</i>
    <i name="ALGO" type="string">Normal</i>
    <i name="ENCUT">520.0</i>
  </incar>
  <kpoints>
    <varray name="kpointlist"><v>0 0 0</v></varray>
    <varray name="weights"><v>1</v></varray>
  </kpoints>
  <parameters>
    <separator name="electronic">
      <i name="EDIFF">1e-5</i>
      <i name="NELM" type="int">100</i>
      <i name="NELMIN" type="int">2</i>
      <i name="IALGO" type="int">38</i>
      <i name="PREC" type="string">accura</i>
      <i name="LREAL" type="logical">T</i>
      <v name="ROPT">-0.00025 -0.00025</v>
      <i name="ENCUT">520.0</i>
    </separator>
    <separator name="ionic">
      <i name="NSW" type="int">2</i>
      <i name="POTIM">1.0</i>
      <i name="MDALGO" type="int">2</i>
      <i name="SMASS">-3.0</i>
      <i name="ISIF" type="int">2</i>
      <i name="ISYM" type="int">0</i>
      <i name="SYSTEM" type="string">Na-LTA 300K NVT AIMD</i>
    </separator>
  </parameters>
  <atominfo>
    <atoms>1</atoms><types>1</types>
    <array name="atoms"><set><rc><c>Na</c><c>1</c></rc></set></array>
    <array name="atomtypes"><set>
      <rc><c>1</c><c>Na</c><c>22.99</c><c>1</c><c>PAW</c></rc>
    </set></array>
  </atominfo>
  <structure name="initialpos">
    <crystal><varray name="basis">
      <v>10 0 0</v><v>0 10 0</v><v>0 0 10</v>
    </varray></crystal>
    <varray name="positions"><v>0 0 0</v></varray>
  </structure>
  {_calculation(0)}
  {_calculation(1, omit_nosepot=omit_second_nosepot)}
</modeling>
"""


def _write(tmp_path: Path, **kwargs) -> Path:
    path = tmp_path / "vasprun.xml"
    path.write_text(_vasprun(**kwargs), encoding="utf-8")
    return path


def test_ens0_reconstructs_controls_exact_energies_and_comment_only_system(tmp_path: Path):
    path = _write(tmp_path)
    result = read_vasp_run_controls(path)

    assert isinstance(result, VaspSourceControlBundle)
    assert isinstance(result.run_controls, SimulationRunControls)
    assert result.run_controls.source_program == "vasp"
    assert result.run_controls.source_program_version == "6.4.2"
    assert result.run_controls.explicit_value("MDALGO") == 2
    assert result.run_controls.effective_value("SMASS") == pytest.approx(-3.0)
    assert result.run_controls.effective_value("ISIF") == 2
    assert result.run_controls.effective_value("LREAL") is True
    assert result.run_controls.explicit_value("LREAL") == "Auto"

    assert len(result.run_controls.user_labels) == 1
    label = result.run_controls.user_labels[0]
    assert label.source_name == "SYSTEM"
    assert label.value == "Na-LTA 300K NVT AIMD"
    assert label.authority is ControlAuthority.COMMENT_ONLY
    assert "ensemble" in label.notes[0]

    assert result.energy_catalog.channel_names == (
        "e_0_energy",
        "e_fr_energy",
        "e_wo_entrp",
        "kinetic",
        "lattice kinetic",
        "nosekinetic",
        "nosepot",
        "total",
    )
    np.testing.assert_allclose(
        result.energy_catalog.channel("kinetic").as_array(), [0.5, 0.5]
    )
    assert result.energy_catalog.channel("total").semantic_role == (
        "source_reported_total_energy"
    )
    assert result.energy_catalog.channel("e_fr_energy").semantic_role == (
        "electronic_free_energy"
    )

    quality = result.numerical_quality_controls
    assert quality.potim_fs == pytest.approx(1.0)
    assert quality.requested_ionic_steps == 2
    assert quality.present_ionic_steps == 2
    assert quality.ionic_output_stride == 1
    assert quality.ediff_ev == pytest.approx(1.0e-5)
    assert quality.nelm == 100
    assert quality.nelmin == 2
    assert quality.algo == "Normal"
    assert quality.ialgo == 38
    assert quality.prec_explicit == "Accurate"
    assert quality.prec_effective == "accura"
    assert quality.lreal_explicit == "Auto"
    assert quality.lreal_effective is True
    assert quality.ropt == pytest.approx((-0.00025, -0.00025))
    assert quality.scf_iteration_counts == (2, 3)
    assert quality.scf_iteration_limit_reached == (False, False)
    assert quality.positions_complete
    assert quality.cells_complete
    assert quality.forces_complete
    assert quality.stresses_complete
    assert quality.native_velocity_frame_count == 0

    iconst = result.manifest.by_role("constraint_definition")
    assert iconst is not None
    assert iconst.state is CompanionFileState.NOT_PROVIDED
    assert result.source_identity.primary_file_name == "vasprun.xml"
    assert result.source_identity.atom_count == 1
    assert result.source_identity.ionic_step_count == 2
    assert result.source_identity.coordinate_payload_sha256 is not None


def test_ens0_preserves_partial_named_energy_channels(tmp_path: Path):
    result = read_vasp_run_controls(_write(tmp_path, omit_second_nosepot=True))
    nosepot = result.energy_catalog.channel("nosepot")
    assert nosepot is not None
    assert nosepot.values == (0.0, None)
    assert nosepot.present_count == 1
    assert nosepot.completeness_fraction == pytest.approx(0.5)
    assert not nosepot.complete
    assert dict(result.numerical_quality_controls.energy_channel_completeness)[
        "nosepot"
    ] == pytest.approx(0.5)


def test_ens0_companion_files_are_bound_only_when_explicitly_supplied(tmp_path: Path):
    path = _write(tmp_path)
    iconst = tmp_path / "ICONST"
    iconst.write_text("synthetic constraint\n", encoding="utf-8")

    unbound = read_vasp_run_controls(path)
    assert unbound.manifest.by_role("constraint_definition").state is (
        CompanionFileState.NOT_PROVIDED
    )

    bound = read_vasp_run_controls(
        path, companion_files={"constraint_definition": iconst}
    )
    record = bound.manifest.by_role("constraint_definition")
    assert record.state is CompanionFileState.PRESENT_AND_BOUND
    assert record.sha256 is not None
    assert bound.source_identity.signature != unbound.source_identity.signature


def test_ens0_records_round_trip_and_reject_tampered_signature(tmp_path: Path):
    result = read_vasp_run_controls(_write(tmp_path))
    payload = result.to_dict()
    rebuilt = VaspSourceControlBundle.from_dict(payload)
    assert rebuilt == result
    assert rebuilt.signature == result.signature

    assert VaspRunControls.from_dict(result.run_controls.to_dict()) == result.run_controls
    assert FrameEnergyCatalog.from_dict(result.energy_catalog.to_dict()) == result.energy_catalog
    assert NumericalMDQualityControls.from_dict(
        result.numerical_quality_controls.to_dict()
    ) == result.numerical_quality_controls
    assert SourceTrajectoryBundleIdentity.from_dict(
        result.source_identity.to_dict()
    ) == result.source_identity

    tampered = result.source_identity.to_dict()
    tampered["ionic_step_count"] = 3
    with pytest.raises(SourceControlSerializationError, match="signature"):
        SourceTrajectoryBundleIdentity.from_dict(tampered)


def test_vasp_frame_reader_attaches_ens0_metadata(tmp_path: Path):
    path = _write(tmp_path)
    trajectory = mdstats.read_vasp_frames(str(path))
    metadata = trajectory.metadata
    assert metadata["source_trajectory_bundle_signature"]
    assert metadata["vasp_source_control_bundle_signature"]
    assert metadata["vasp_run_controls"]["schema"] == "mdstats.vasp-run-controls.v1"
    assert metadata["vasp_run_controls"]["user_labels"][0]["authority"] == (
        "comment_only"
    )
    catalog = FrameEnergyCatalog.from_dict(metadata["frame_energy_catalog"])
    np.testing.assert_allclose(catalog.channel("total").as_array(), [-9.5, -9.4])
    assert metadata["numerical_md_quality_controls"]["present_ionic_steps"] == 2


def test_ens0_public_exports():
    assert mdstats.read_vasp_run_controls is read_vasp_run_controls
    assert "VaspSourceControlBundle" in mdstats.__all__
    assert "FrameEnergyCatalog" in mdstats.__all__


def test_interrupted_xml_recovers_complete_records_and_records_integrity(tmp_path: Path):
    path = tmp_path / "interrupted.xml"
    path.write_text(_vasprun().removesuffix("</modeling>\n"), encoding="utf-8")

    with pytest.warns(UserWarning, match="interrupted VASP XML"):
        result = read_vasp_run_controls(path)

    quality = result.numerical_quality_controls
    assert result.source_identity.ionic_step_count == 2
    assert quality.source_parse_complete is False
    assert quality.source_parse_warning is not None
    assert quality.discarded_incomplete_ionic_tail is False
    assert quality.recovered_unclosed_ionic_step is False
    assert quality.positions_complete
    assert quality.cells_complete
    assert quality.forces_complete
    assert quality.stresses_complete


def test_interrupted_xml_recovers_unclosed_final_calculation_when_payload_is_complete(tmp_path: Path):
    complete = _vasprun()
    marker = "  </calculation>\n\n</modeling>\n"
    assert complete.endswith(marker)
    path = tmp_path / "unclosed-final-calculation.xml"
    path.write_text(complete[: -len(marker)], encoding="utf-8")

    with pytest.warns(UserWarning, match="closing XML tag was missing"):
        result = read_vasp_run_controls(path)

    quality = result.numerical_quality_controls
    assert result.source_identity.ionic_step_count == 2
    assert quality.recovered_unclosed_ionic_step is True
    assert quality.discarded_incomplete_ionic_tail is False
    assert quality.positions_complete
    assert quality.forces_complete
    assert result.energy_catalog.channel("e_fr_energy").values == pytest.approx(
        (-10.0, -9.9)
    )


def test_interrupted_xml_discards_only_ambiguous_partial_tail(tmp_path: Path):
    complete = _vasprun()
    second = complete.index("  <calculation>", complete.index("  <calculation>") + 1)
    partial = complete[:second] + "  <calculation><structure>"
    path = tmp_path / "partial-tail.xml"
    path.write_text(partial, encoding="utf-8")

    with pytest.warns(UserWarning, match="incomplete final calculation was ignored"):
        result = read_vasp_run_controls(path)

    quality = result.numerical_quality_controls
    assert result.source_identity.ionic_step_count == 1
    assert quality.discarded_incomplete_ionic_tail is True
    assert quality.recovered_unclosed_ionic_step is False
    assert quality.positions_complete
    assert quality.forces_complete


def test_interrupted_xml_without_critical_records_is_rejected(tmp_path: Path):
    path = tmp_path / "ambiguous.xml"
    path.write_text("<modeling><incar><i name='POTIM'>1.0</i></incar>", encoding="utf-8")
    with pytest.raises(mdstats.SourceControlError, match="ambiguous"):
        read_vasp_run_controls(path)


def test_nontrailing_xml_corruption_remains_a_hard_failure(tmp_path: Path):
    content = _vasprun().replace("</incar>", "</parameters>", 1)
    path = tmp_path / "malformed.xml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(mdstats.SourceControlError, match="Could not parse VASP XML"):
        read_vasp_run_controls(path)
