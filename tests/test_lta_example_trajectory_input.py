from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pytest


def _load_example_module():
    path = Path(__file__).parents[1] / "examples" / "plot_lta_mixed_alkali_density.py"
    spec = importlib.util.spec_from_file_location("mdstats_lta_example_input", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(path: Path, **overrides) -> argparse.Namespace:
    values = {
        "trajectory": path,
        "format": "auto",
        "stride": 1,
        "timestep_fs": None,
        "lammps_log": None,
        "lammps_units": None,
        "lammps_timestep": None,
        "lammps_type_map": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("vasprun.xml", "vasp-xml"),
        ("run.XDATCAR", "vasp-xdatcar"),
        ("TRAJECTORY", "vasp-contcar-trajectory"),
        ("backup.TRAJECTORY.gz", "vasp-contcar-trajectory"),
        ("trajectory.lammpstrj", "lammps-dump"),
        ("traj.dump", "lammps-dump"),
        ("dump.production", "lammps-dump"),
        ("dump.lammpstrj.gz", "lammps-dump"),
    ],
)
def test_infer_supported_trajectory_formats(name: str, expected: str) -> None:
    module = _load_example_module()
    assert module.infer_trajectory_format(Path(name)) == expected


def test_explicit_format_handles_ambiguous_filename() -> None:
    module = _load_example_module()
    assert (
        module.infer_trajectory_format(Path("frames.dat"), "lammps-dump")
        == "lammps-dump"
    )
    with pytest.raises(ValueError, match="Cannot infer trajectory format"):
        module.infer_trajectory_format(Path("frames.dat"))


def test_lammps_type_map_parser() -> None:
    module = _load_example_module()
    assert module.parse_lammps_type_map("1=Si, 2=Al,3=O,4=Na") == {
        1: "Si",
        2: "Al",
        3: "O",
        4: "Na",
    }
    with pytest.raises(ValueError, match="TYPE=ELEMENT"):
        module.parse_lammps_type_map("1:Si")
    with pytest.raises(ValueError, match="mapped more than once"):
        module.parse_lammps_type_map("1=Si,1=Al")


def test_lammps_dump_with_element_column_is_read_directly(tmp_path: Path) -> None:
    module = _load_example_module()
    dump = tmp_path / "production.lammpstrj"
    dump.write_text(
        """ITEM: TIMESTEP
0
ITEM: TIME
0.0
ITEM: UNITS
metal
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xsu ysu zsu vx vy vz
1 Na 0.10 0.20 0.30 0 0 0
2 O  0.40 0.50 0.60 0 0 0
ITEM: TIMESTEP
10
ITEM: TIME
0.01
ITEM: UNITS
metal
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xsu ysu zsu vx vy vz
1 Na 0.20 0.20 0.30 0 0 0
2 O  0.40 0.50 0.60 0 0 0
""",
        encoding="utf-8",
    )

    trajectory, source_format = module.read_input_trajectory(_args(dump))

    assert source_format == "lammps-dump"
    assert trajectory.n_frames == 2
    assert trajectory.n_atoms == 2
    assert trajectory.atomic_numbers.tolist() == [11, 8]
    np.testing.assert_allclose(trajectory.times, [0.0, 0.01])


def test_lammps_numeric_types_accept_cli_mapping_and_log(tmp_path: Path) -> None:
    module = _load_example_module()
    dump = tmp_path / "dump.production"
    log = tmp_path / "log.lammps"
    dump.write_text(
        """ITEM: TIMESTEP
0
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type xsu ysu zsu vx vy vz
1 1 0.10 0.20 0.30 0 0 0
2 2 0.40 0.50 0.60 0 0 0
ITEM: TIMESTEP
10
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id type xsu ysu zsu vx vy vz
1 1 0.20 0.20 0.30 0 0 0
2 2 0.40 0.50 0.60 0 0 0
""",
        encoding="utf-8",
    )
    log.write_text(
        """units metal
timestep 0.001
Step Time Temp PotEng
0 0.000 300 -10
10 0.010 310 -9
Loop time of 1 on 1 procs
""",
        encoding="utf-8",
    )

    trajectory, source_format = module.read_input_trajectory(
        _args(
            dump,
            lammps_log=log,
            lammps_type_map="1=Na,2=O",
        )
    )

    assert source_format == "lammps-dump"
    assert trajectory.atomic_numbers.tolist() == [11, 8]
    np.testing.assert_allclose(trajectory.temperatures, [300.0, 310.0])
    np.testing.assert_allclose(trajectory.potential_energies, [-10.0, -9.0])


def test_custom_trajectory_keeps_legacy_one_fs_default(monkeypatch, tmp_path: Path) -> None:
    module = _load_example_module()
    seen: dict[str, object] = {}
    sentinel = object()

    def fake_read_vasp_frames(filename, **kwargs):
        seen["filename"] = filename
        seen.update(kwargs)
        return sentinel

    monkeypatch.setattr(module, "read_vasp_frames", fake_read_vasp_frames)
    path = tmp_path / "TRAJECTORY"
    trajectory, source_format = module.read_input_trajectory(_args(path, stride=3))

    assert trajectory is sentinel
    assert source_format == "vasp-contcar-trajectory"
    assert seen["format"] == "vasp-contcar-trajectory"
    assert seen["stride"] == 3
    assert seen["timestep_fs"] == 1.0


def test_vasprun_does_not_override_embedded_timestep(monkeypatch, tmp_path: Path) -> None:
    module = _load_example_module()
    seen: dict[str, object] = {}
    sentinel = object()

    def fake_read_vasp_frames(filename, **kwargs):
        seen.update(kwargs)
        return sentinel

    monkeypatch.setattr(module, "read_vasp_frames", fake_read_vasp_frames)
    trajectory, source_format = module.read_input_trajectory(
        _args(tmp_path / "vasprun.xml")
    )

    assert trajectory is sentinel
    assert source_format == "vasp-xml"
    assert seen["timestep_fs"] is None
