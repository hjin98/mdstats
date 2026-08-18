from __future__ import annotations

import numpy as np

from mdstats.io.common import RawFrameCollection
from mdstats.preprocess.normalize import normalize_raw_frame_collection
from mdstats.preprocess.unwrap import infer_unwrapped_fractional_positions
from mdstats.preprocess.velocity import reconstruct_velocities


def test_minimum_image_unwrap_boundary_crossing() -> None:
    wrapped = np.array(
        [
            [[0.90, 0.2, 0.3]],
            [[0.05, 0.2, 0.3]],
            [[0.20, 0.2, 0.3]],
        ]
    )
    unwrapped = infer_unwrapped_fractional_positions(
        wrapped, np.array([True, True, True])
    )
    np.testing.assert_allclose(unwrapped[:, 0, 0], [0.90, 1.05, 1.20])


def test_nonuniform_velocity_reconstruction_is_exact_for_quadratic() -> None:
    times = np.array([0.0, 0.2, 0.7, 1.5])
    positions = np.zeros((len(times), 1, 3))
    positions[:, 0, 0] = times**2
    velocity = reconstruct_velocities(positions, times)
    np.testing.assert_allclose(velocity[:, 0, 0], 2.0 * times, atol=1e-12)


def test_variable_cell_cartesian_positions_and_pressure_property() -> None:
    cells = np.array([np.eye(3) * 10.0, np.eye(3) * 11.0, np.eye(3) * 12.0])
    scaled = np.array(
        [
            [[0.9, 0.0, 0.0]],
            [[1.0, 0.0, 0.0]],
            [[1.1, 0.0, 0.0]],
        ]
    )
    stresses = np.array([-np.eye(3) * value for value in (1.0, 2.0, 3.0)])
    raw = RawFrameCollection(
        source_ids=None,
        source_type_ids=None,
        atomic_numbers=np.full((3, 1), 11, dtype=np.int32),
        masses=np.full((3, 1), 22.98976928),
        frame_ids=np.arange(3, dtype=np.int64),
        steps=np.array([0, 1, 2]),
        times=np.array([0.0, 0.1, 0.2]),
        cells=cells,
        origins=np.zeros((3, 3)),
        pbc=np.ones(3, dtype=bool),
        coordinate_kind="unwrapped_fractional",
        coordinates=scaled,
        velocities=np.zeros((3, 1, 3)),
        stresses=stresses,
    )
    trajectory = normalize_raw_frame_collection(
        raw,
        frame_semantics="trajectory",
        source_format="vasp-vasprun-xml",
        source_files=("synthetic.xml",),
        units_source="test",
        stress_source="test",
    )
    np.testing.assert_allclose(trajectory.get_positions()[:, 0, 0], [9.0, 11.0, 13.2])
    np.testing.assert_allclose(trajectory.pressures, [1.0, 2.0, 3.0])
    np.testing.assert_allclose(trajectory.volumes, [1000.0, 1331.0, 1728.0])
