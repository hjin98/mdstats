from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.io import write

from mdstats import (
    compute_coordination_distribution,
    compute_msd,
    compute_pair_rdf,
    read_lammps_frames,
    read_structure,
)
from mdstats.exceptions import MissingVelocityError, TrajectoryRequiredError


def _write(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_read_poscar_as_single_frame_and_run_structural_analysis(
    tmp_path: Path,
) -> None:
    atoms = Atoms(
        symbols=["Na", "Cl"],
        scaled_positions=[[0.0, 0.0, 0.0], [0.2, 0.2, 0.2]],
        cell=np.eye(3) * 10.0,
        pbc=True,
    )
    filename = tmp_path / "POSCAR"
    write(filename, atoms, format="vasp")

    trajectory = read_structure(filename)

    assert trajectory.n_frames == 1
    assert trajectory.is_single_frame
    assert trajectory.metadata["single_frame"] is True
    assert trajectory.metadata["static_structure"] is True
    assert trajectory.velocities is None
    assert not trajectory.has_velocities
    assert not trajectory.has_forces
    assert trajectory.provenance.velocity_source == "unavailable"
    np.testing.assert_array_equal(trajectory.atomic_numbers, [11, 17])

    rdf = compute_pair_rdf(
        trajectory,
        species_a="Na",
        species_b="Cl",
        r_max=4.0,
        n_bins=80,
    )
    assert rdf.n_frames == 1
    assert int(rdf.counts.sum()) == 1

    coordination = compute_coordination_distribution(
        trajectory,
        species_a="Na",
        species_b="Cl",
        cutoff=4.0,
    )
    assert coordination.n_frames == 1
    np.testing.assert_array_equal(coordination.per_atom_per_frame, [[1]])


def test_single_frame_rejects_dynamic_analysis_and_missing_velocity_request(
    tmp_path: Path,
) -> None:
    atoms = Atoms("Na", positions=[[0.0, 0.0, 0.0]], cell=np.eye(3) * 8.0, pbc=True)
    filename = tmp_path / "CONTCAR"
    write(filename, atoms, format="vasp")
    trajectory = read_structure(filename)

    with pytest.raises(
        TrajectoryRequiredError, match="MSD requires a time-ordered trajectory"
    ):
        compute_msd(trajectory)
    with pytest.raises(MissingVelocityError, match="VACF requires atomic velocities"):
        trajectory.require_velocities("VACF")


def test_read_lammps_data_with_type_map_and_native_velocity(tmp_path: Path) -> None:
    filename = tmp_path / "structure.data"
    _write(
        filename,
        """
LAMMPS data

2 atoms
2 atom types

0 10 xlo xhi
0 10 ylo yhi
0 10 zlo zhi

Masses

1 22.98976928
2 35.45

Atoms # atomic

2 2 5.0 5.0 5.0
1 1 1.0 1.0 1.0

Velocities

1 1.0 0.0 0.0
2 2.0 0.0 0.0
""",
    )

    trajectory = read_structure(
        filename,
        type_map={1: "Na", 2: "Cl"},
        format="lammps-data",
    )

    assert trajectory.is_single_frame
    assert not trajectory.has_velocities
    assert trajectory.provenance.velocity_source == "discarded_for_ensemble"
    assert trajectory.metadata["native_velocities_discarded"] is True
    # ASE's LAMMPS data reader sorts by atom ID by default.
    np.testing.assert_array_equal(trajectory.atomic_numbers, [11, 17])


def test_single_frame_lammps_dump_needs_neither_time_nor_velocity(
    tmp_path: Path,
) -> None:
    filename = tmp_path / "one.dump"
    _write(
        filename,
        """
ITEM: TIMESTEP
100
ITEM: NUMBER OF ATOMS
2
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xs ys zs
2 Cl 0.5 0.5 0.5
1 Na 0.1 0.1 0.1
""",
    )

    trajectory = read_lammps_frames(filename, units="metal", frame_semantics="ensemble")

    assert trajectory.is_single_frame
    assert trajectory.velocities is None
    assert trajectory.times is None
    np.testing.assert_array_equal(trajectory.atomic_numbers, [11, 17])
    np.testing.assert_allclose(
        trajectory.fractional_positions[0],
        [[0.1, 0.1, 0.1], [0.5, 0.5, 0.5]],
    )
    assert trajectory.metadata["time_source"] == "unavailable for independent ensemble"


def test_read_cif_autodetection(tmp_path: Path) -> None:
    atoms = Atoms(
        "SiO2",
        scaled_positions=[[0.0, 0.0, 0.0], [0.25, 0.25, 0.25], [0.75, 0.75, 0.75]],
        cell=np.eye(3) * 5.0,
        pbc=True,
    )
    filename = tmp_path / "structure.cif"
    write(filename, atoms, format="cif")

    trajectory = read_structure(filename)
    assert trajectory.is_single_frame
    assert trajectory.metadata["ase_formats"] == ("cif",)
    np.testing.assert_array_equal(trajectory.atomic_numbers, [14, 8, 8])


def test_multiframe_trajectory_cannot_omit_velocities() -> None:
    from mdstats import AtomisticFrameCollection, FrameCollectionProvenance
    from mdstats.exceptions import FrameCollectionError

    provenance = FrameCollectionProvenance(
        source_format="ase-structure",
        source_files=("synthetic",),
        velocity_source="unavailable",
        coordinate_normalization="native_unwrapped_fractional",
        stress_source=None,
        units_source="test",
    )
    with pytest.raises(FrameCollectionError, match="multi-frame trajectory requires"):
        AtomisticFrameCollection(
            frame_semantics="trajectory",
            frame_ids=np.arange(2, dtype=np.int64),
            atomic_numbers=np.asarray([11], dtype=np.int32),
            masses=np.asarray([22.98976928]),
            pbc=np.ones(3, dtype=bool),
            steps=np.asarray([0, 1]),
            times=np.asarray([0.0, 0.1]),
            cells=np.repeat(np.eye(3)[None, :, :] * 10.0, 2, axis=0),
            origins=np.zeros((2, 3)),
            fractional_positions=np.zeros((2, 1, 3)),
            velocities=None,
            provenance=provenance,
        )
