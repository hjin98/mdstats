from __future__ import annotations

from pathlib import Path

import numpy as np

from mdstats import read_vasp_frames


def _calculation(x: float, velocity: float | None, energy: float) -> str:
    velocity_xml = ""
    if velocity is not None:
        velocity_xml = f"""
        <varray name=\"velocities\"><v>{velocity} 0 0</v></varray>
        """
    return f"""
  <calculation>
    <scstep><energy>
      <i name=\"e_fr_energy\">{energy}</i>
      <i name=\"e_0_energy\">{energy}</i>
    </energy></scstep>
    <structure>
      <crystal><varray name=\"basis\">
        <v>10 0 0</v><v>0 10 0</v><v>0 0 10</v>
      </varray></crystal>
      <varray name=\"positions\"><v>{x} 0 0</v></varray>
      {velocity_xml}
    </structure>
    <varray name=\"forces\"><v>0.1 0.0 0.0</v></varray>
    <varray name=\"stress\">
      <v>-100 0 0</v><v>0 -100 0</v><v>0 0 -100</v>
    </varray>
    <energy>
      <i name=\"e_fr_energy\">{energy}</i>
      <i name=\"kinetic\">0.5</i>
      <i name=\"total\">{energy + 0.5}</i>
    </energy>
  </calculation>
"""


def _vasprun(velocities: bool) -> str:
    vel = [0.001, 0.001, 0.001] if velocities else [None, None, None]
    calculations = "".join(
        _calculation(x, v, -1.0 + i * 0.1)
        for i, (x, v) in enumerate(zip([0.9, 0.0, 0.1], vel, strict=True))
    )
    return f"""<?xml version=\"1.0\"?>
<modeling>
  <generator><i name=\"version\" type=\"string\">test</i></generator>
  <incar><i name=\"IBRION\" type=\"int\">0</i></incar>
  <kpoints>
    <varray name=\"kpointlist\"><v>0 0 0</v></varray>
    <varray name=\"weights\"><v>1</v></varray>
  </kpoints>
  <parameters>
    <separator name=\"ionic\"><i name=\"POTIM\">1.0</i></separator>
  </parameters>
  <atominfo>
    <atoms>1</atoms><types>1</types>
    <array name=\"atoms\"><set><rc><c>Na</c><c>1</c></rc></set></array>
    <array name=\"atomtypes\"><set>
      <rc><c>1</c><c>Na</c><c>22.99</c><c>1</c><c>PAW</c></rc>
    </set></array>
  </atominfo>
  <structure name=\"initialpos\">
    <crystal><varray name=\"basis\">
      <v>10 0 0</v><v>0 10 0</v><v>0 0 10</v>
    </varray></crystal>
    <varray name=\"positions\"><v>0.9 0 0</v></varray>
  </structure>
  {calculations}
</modeling>
"""


def test_vasp_reconstructs_velocities_and_unwraps(tmp_path: Path) -> None:
    xml = tmp_path / "vasprun.xml"
    xml.write_text(_vasprun(velocities=False), encoding="utf-8")
    trajectory = read_vasp_frames(str(xml))
    np.testing.assert_allclose(
        trajectory.fractional_positions[:, 0, 0], [0.9, 1.0, 1.1]
    )
    # One angstrom per femtosecond = 1000 Å/ps.
    np.testing.assert_allclose(trajectory.velocities[:, 0, 0], 1000.0)
    np.testing.assert_allclose(trajectory.forces[:, 0, 0], 0.1)
    np.testing.assert_allclose(trajectory.masses, [22.99])
    np.testing.assert_allclose(trajectory.kinetic_energies, [0.5, 0.5, 0.5])
    assert trajectory.provenance.velocity_source == "finite_difference"
    assert trajectory.provenance.coordinate_normalization == "minimum_image_inferred"


def test_vasp_uses_complete_native_velocity_trajectory(tmp_path: Path) -> None:
    xml = tmp_path / "vasprun-native.xml"
    xml.write_text(_vasprun(velocities=True), encoding="utf-8")
    trajectory = read_vasp_frames(str(xml))
    np.testing.assert_allclose(trajectory.velocities[:, 0, 0], 1.0)
    assert trajectory.provenance.velocity_source == "native"


def _xdatcar() -> str:
    return """Na trajectory
1.0
10.0 0.0 0.0
0.0 10.0 0.0
0.0 0.0 10.0
Na
1
Direct configuration=     1
0.900000 0.000000 0.000000
Direct configuration=     2
0.000000 0.000000 0.000000
Direct configuration=     3
0.100000 0.000000 0.000000
"""


def test_vasp_autodetects_xdatcar_and_reconstructs_velocities(tmp_path: Path) -> None:
    xdatcar = tmp_path / "XDATCAR"
    xdatcar.write_text(_xdatcar(), encoding="utf-8")

    trajectory = read_vasp_frames(str(xdatcar), timestep_fs=1.0)

    np.testing.assert_allclose(
        trajectory.fractional_positions[:, 0, 0], [0.9, 1.0, 1.1]
    )
    np.testing.assert_allclose(trajectory.velocities[:, 0, 0], 1000.0)
    assert trajectory.provenance.source_format == "vasp-xdatcar"
    assert trajectory.metadata["vasp_input_format"] == "vasp-xdatcar"


def test_vasp_autodetects_filename_ending_in_xdatcar(tmp_path: Path) -> None:
    xdatcar = tmp_path / "unfinished_run.XDATCAR"
    xdatcar.write_text(_xdatcar(), encoding="utf-8")

    trajectory = read_vasp_frames(str(xdatcar), timestep_fs=2.0)

    assert trajectory.n_frames == 3
    np.testing.assert_allclose(trajectory.times, [0.0, 0.002, 0.004])
    assert trajectory.provenance.source_format == "vasp-xdatcar"


def test_vasp_xdatcar_requires_explicit_timestep(tmp_path: Path) -> None:
    from mdstats.exceptions import MissingTimeError

    xdatcar = tmp_path / "XDATCAR"
    xdatcar.write_text(_xdatcar(), encoding="utf-8")

    with np.testing.assert_raises_regex(
        MissingTimeError, "XDATCAR does not store POTIM"
    ):
        read_vasp_frames(str(xdatcar))
