"""Tests for independent frame ensembles and semantic analysis guards."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.io import write

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_coordination_distribution,
    compute_msd,
    compute_pair_rdf,
    read_lammps_frames,
    read_structure_collection,
    read_vasp_frames,
)
from mdstats.exceptions import TrajectoryRequiredError


def _trajectory_crossing_boundary() -> AtomisticFrameCollection:
    scaled = np.array([[[0.9, 0.0, 0.0]], [[1.0, 0.0, 0.0]], [[1.1, 0.0, 0.0]]])
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(3, dtype=np.int64),
        atomic_numbers=np.array([11], dtype=np.int32),
        masses=np.array([22.98976928]),
        pbc=np.ones(3, dtype=bool),
        steps=np.array([0, 1, 2], dtype=np.int64),
        times=np.array([0.0, 0.1, 0.2]),
        cells=np.repeat(np.eye(3)[None, :, :] * 10.0, 3, axis=0),
        origins=np.zeros((3, 3)),
        fractional_positions=scaled,
        velocities=np.ones((3, 1, 3)),
        provenance=FrameCollectionProvenance(
            source_format="lammps-custom-dump",
            source_files=("synthetic.dump",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_trajectory_subset_can_be_reinterpreted_as_independent_ensemble() -> None:
    trajectory = _trajectory_crossing_boundary()
    ensemble = trajectory.select_frames([0, 2], frame_semantics="ensemble")

    assert ensemble.is_ensemble
    assert not ensemble.has_velocities
    assert ensemble.provenance.velocity_source == "discarded_for_ensemble"
    assert ensemble.provenance.coordinate_normalization == "independent_frame_wrapping"
    np.testing.assert_allclose(ensemble.fractional_positions[:, 0, 0], [0.9, 0.1])
    assert ensemble.metadata["parent_frame_ids"] == [0, 2]

    with pytest.raises(TrajectoryRequiredError):
        compute_msd(ensemble)


def test_ensemble_cannot_be_reinterpreted_as_trajectory() -> None:
    ensemble = _trajectory_crossing_boundary().as_ensemble()
    with pytest.raises(ValueError, match="cannot be reinterpreted as a trajectory"):
        ensemble.select_frames(slice(None), frame_semantics="trajectory")


def test_structure_collection_reads_independent_poscar_frames(tmp_path: Path) -> None:
    files: list[Path] = []
    for index, displacement in enumerate((0.0, 0.1)):
        atoms = Atoms(
            symbols=["Na", "Cl"],
            scaled_positions=[[displacement, 0.0, 0.0], [0.2, 0.0, 0.0]],
            cell=np.eye(3) * 10.0,
            pbc=True,
        )
        path = tmp_path / f"POSCAR.{index}"
        write(path, atoms, format="vasp")
        files.append(path)

    ensemble = read_structure_collection(files, format="vasp")

    assert ensemble.is_ensemble
    assert ensemble.n_frames == 2
    assert ensemble.times is None
    assert ensemble.steps is None
    assert ensemble.velocities is None

    rdf = compute_pair_rdf(ensemble, "Na", "Cl", r_max=4.0, n_bins=40)
    coordination = compute_coordination_distribution(ensemble, "Na", "Cl", cutoff=3.0)
    assert rdf.n_frames == 2
    assert coordination.n_frames == 2


def test_lammps_ensemble_needs_no_time_and_discards_velocity(tmp_path: Path) -> None:
    dump = tmp_path / "samples.dump"
    dump.write_text(
        """ITEM: TIMESTEP
100
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xs ys zs vx vy vz
1 Na 0.9 0 0 1 0 0
ITEM: TIMESTEP
700
ITEM: NUMBER OF ATOMS
1
ITEM: BOX BOUNDS pp pp pp
0 10
0 10
0 10
ITEM: ATOMS id element xs ys zs vx vy vz
1 Na 0.1 0 0 2 0 0
""",
        encoding="utf-8",
    )

    ensemble = read_lammps_frames(
        dump,
        units="metal",
        frame_semantics=FrameSemantics.ENSEMBLE,
    )

    assert ensemble.is_ensemble
    assert ensemble.times is None
    assert ensemble.velocities is None
    np.testing.assert_allclose(ensemble.fractional_positions[:, 0, 0], [0.9, 0.1])
    assert ensemble.provenance.velocity_source == "discarded_for_ensemble"


def test_xdatcar_ensemble_does_not_require_timestep(tmp_path: Path) -> None:
    xdatcar = tmp_path / "XDATCAR"
    xdatcar.write_text(
        """Na samples
1.0
10.0 0.0 0.0
0.0 10.0 0.0
0.0 0.0 10.0
Na
1
Direct configuration=     1
0.900000 0.000000 0.000000
Direct configuration=     2
0.100000 0.000000 0.000000
""",
        encoding="utf-8",
    )

    ensemble = read_vasp_frames(xdatcar, frame_semantics="ensemble")

    assert ensemble.is_ensemble
    assert ensemble.times is None
    assert ensemble.velocities is None
    np.testing.assert_allclose(ensemble.fractional_positions[:, 0, 0], [0.9, 0.1])
