from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mdstats import read_lammps_frames
from mdstats.exceptions import SpeciesConsistencyError


def _write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_lammps_xsu_sorts_ids_and_reads_thermo(tmp_path: Path) -> None:
    dump = tmp_path / "traj.dump"
    log = tmp_path / "log.lammps"
    _write(
        dump,
        """
ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type xsu ysu zsu vx vy vz fx fy fz
2 2 0.8 0.2 0.3 2 0 0 0.2 0 0
1 1 0.1 0.2 0.3 1 0 0 0.1 0 0
ITEM: TIMESTEP
10
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 11
0 10
0 10
ITEM: ATOMS id type xsu ysu zsu vx vy vz fx fy fz
1 1 0.2 0.2 0.3 1 0 0 0.1 0 0
2 2 1.0 0.2 0.3 2 0 0 0.2 0 0
""",
    )
    _write(
        log,
        """
units metal
timestep 0.001
Step Time Temp PotEng KinEng TotEng Press Pxx Pyy Pzz Pxy Pxz Pyz
0 0.000 300 -10 1 -9 100 100 100 100 0 0 0
10 0.010 310 -9 1.1 -7.9 200 200 200 200 0 0 0
Loop time of 1 on 1 procs
""",
    )

    trajectory = read_lammps_frames(
        str(dump),
        log_file=str(log),
        type_map={1: "Na", 2: "Cl"},
    )

    assert trajectory.n_atoms == 2
    assert trajectory.n_frames == 2
    assert trajectory.atomic_numbers.tolist() == [11, 17]
    np.testing.assert_allclose(trajectory.fractional_positions[:, 0, 0], [0.1, 0.2])
    np.testing.assert_allclose(trajectory.fractional_positions[:, 1, 0], [0.8, 1.0])
    np.testing.assert_allclose(trajectory.velocities[:, :, 0], [[1.0, 2.0], [1.0, 2.0]])
    np.testing.assert_allclose(trajectory.forces[:, :, 0], [[0.1, 0.2], [0.1, 0.2]])
    np.testing.assert_allclose(trajectory.times, [0.0, 0.01])
    np.testing.assert_allclose(trajectory.temperatures, [300, 310])
    # 100 bar in eV/A^3 and tensile-positive stress.
    assert trajectory.stresses[0, 0, 0] < 0.0
    np.testing.assert_allclose(trajectory.pressures, trajectory.scalar_pressures)
    assert (
        trajectory.provenance.coordinate_normalization == "native_unwrapped_fractional"
    )
    assert trajectory.provenance.velocity_source == "native"


def test_lammps_wrapped_only_reconstructs_crossing_velocity(tmp_path: Path) -> None:
    dump = tmp_path / "wrapped.dump"
    _write(
        dump,
        """
ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xs ys zs
1 Na 0.90 0 0
ITEM: TIMESTEP
1
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xs ys zs
1 Na 0.00 0 0
ITEM: TIMESTEP
2
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xs ys zs
1 Na 0.10 0 0
""",
    )
    with pytest.warns(UserWarning):
        trajectory = read_lammps_frames(str(dump), units="metal", timestep=0.1)
    np.testing.assert_allclose(
        trajectory.fractional_positions[:, 0, 0], [0.9, 1.0, 1.1]
    )
    np.testing.assert_allclose(trajectory.get_positions()[:, 0, 0], [9.0, 10.0, 11.0])
    np.testing.assert_allclose(trajectory.velocities[:, 0, 0], [10.0, 10.0, 10.0])
    assert trajectory.forces is None
    assert trajectory.provenance.velocity_source == "finite_difference"
    assert trajectory.provenance.coordinate_normalization == "minimum_image_inferred"


def test_lammps_triclinic_cartesian_with_images(tmp_path: Path) -> None:
    dump = tmp_path / "triclinic.dump"
    _write(
        dump,
        """
ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS xy xz yz pp pp pp
0 12.5 2.0
0 10.5 0.5
0 10.0 1.0
ITEM: ATOMS id element x y z ix iy iz
1 Na 2.5 2.0 3.0 1 0 0
ITEM: TIMESTEP
1
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS xy xz yz pp pp pp
0 12.5 2.0
0 10.5 0.5
0 10.0 1.0
ITEM: ATOMS id element x y z ix iy iz
1 Na 3.5 2.0 3.0 1 0 0
""",
    )
    with pytest.warns(UserWarning):
        trajectory = read_lammps_frames(str(dump), units="metal", timestep=0.1)
    np.testing.assert_allclose(
        trajectory.cells[0], [[10.0, 0, 0], [2.0, 9.5, 0], [0.5, 1.0, 10.0]]
    )
    assert trajectory.provenance.coordinate_normalization == "image_flags"
    # Wrapped Cartesian x=2.5 plus one A-vector image -> unwrapped x=12.5.
    np.testing.assert_allclose(trajectory.get_positions()[0, 0], [12.5, 2.0, 3.0])


def test_lammps_rejects_type_change_for_same_id(tmp_path: Path) -> None:
    dump = tmp_path / "bad.dump"
    _write(
        dump,
        """
ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type xsu ysu zsu vx vy vz
1 1 0 0 0 0 0 0
ITEM: TIMESTEP
1
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type xsu ysu zsu vx vy vz
1 2 0 0 0 0 0 0
""",
    )
    with pytest.raises(SpeciesConsistencyError):
        read_lammps_frames(
            str(dump),
            units="metal",
            timestep=0.1,
            type_map={1: "Na", 2: "Cl"},
        )


def test_lammps_xu_removes_nonzero_box_origin(tmp_path: Path) -> None:
    dump = tmp_path / "xu-origin.dump"
    _write(
        dump,
        """
ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
5 15
-2 8
1 11
ITEM: ATOMS id element xu yu zu
1 Na 16 0 4
ITEM: TIMESTEP
1
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
5 15
-2 8
1 11
ITEM: ATOMS id element xu yu zu
1 Na 17 0 4
""",
    )
    with pytest.warns(UserWarning):
        trajectory = read_lammps_frames(str(dump), units="metal", timestep=0.1)
    np.testing.assert_allclose(trajectory.origins, [[5, -2, 1], [5, -2, 1]])
    np.testing.assert_allclose(
        trajectory.fractional_positions[:, 0],
        [[1.1, 0.2, 0.3], [1.2, 0.2, 0.3]],
    )
    np.testing.assert_allclose(
        trajectory.get_positions()[:, 0], [[11, 2, 3], [12, 2, 3]]
    )
    assert (
        trajectory.provenance.coordinate_normalization == "native_unwrapped_cartesian"
    )


def test_general_triclinic_thermo_stress_is_rotated(tmp_path: Path) -> None:
    dump = tmp_path / "general.dump"
    log = tmp_path / "general.log"
    root2 = np.sqrt(2.0)
    _write(
        dump,
        f"""
ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS abc origin
{root2} {root2} 0 1
{-root2} {root2} 0 2
0 0 2 3
ITEM: ATOMS id element xsu ysu zsu vx vy vz
1 Na 0.1 0.2 0.3 0 0 0
ITEM: TIMESTEP
1
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS abc origin
{root2} {root2} 0 1
{-root2} {root2} 0 2
0 0 2 3
ITEM: ATOMS id element xsu ysu zsu vx vy vz
1 Na 0.2 0.2 0.3 0 0 0
""",
    )
    _write(
        log,
        """
units metal
timestep 0.1
Step Time Pxx Pyy Pzz Pxy Pxz Pyz
0 0.0 100 200 300 0 0 0
1 0.1 100 200 300 0 0 0
Loop time of 1 on 1 procs
""",
    )
    with pytest.warns(UserWarning, match="boundary flags"):
        trajectory = read_lammps_frames(str(dump), log_file=str(log))
    factor = 1.0e5 / 160_217_663_400.0
    expected = (
        np.array([[-150.0, 50.0, 0.0], [50.0, -150.0, 0.0], [0.0, 0.0, -300.0]])
        * factor
    )
    np.testing.assert_allclose(trajectory.stresses[0], expected, atol=1e-15)
    assert "rotated" in trajectory.provenance.stress_source


def test_lammps_stride_streaming_preserves_source_frame_count(tmp_path: Path) -> None:
    dump = tmp_path / "stride.dump"
    frames = []
    for frame_id in range(5):
        frames.append(
            f"""
ITEM: TIMESTEP
{frame_id * 10}
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xsu ysu zsu vx vy vz
1 Na {0.1 * frame_id:.1f} 0 0 0 0 0
""".strip()
        )
    _write(dump, "\n".join(frames))

    trajectory = read_lammps_frames(
        str(dump),
        units="metal",
        timestep=0.001,
        stride=2,
    )

    assert trajectory.n_frames == 3
    assert trajectory.metadata["source_frame_count"] == 5
    np.testing.assert_allclose(trajectory.times, [0.0, 0.02, 0.04])
    np.testing.assert_allclose(
        trajectory.fractional_positions[:, 0, 0],
        [0.0, 0.2, 0.4],
    )
