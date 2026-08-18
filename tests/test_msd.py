"""Deterministic tests for the MSD analysis module."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_msd,
)
from mdstats.analysis import (
    CollectiveMotionWarning,
    FixedOriginMSDWarning,
    VariableCellMSDWarning,
)


def make_trajectory(
    cartesian_positions: np.ndarray,
    *,
    times: np.ndarray | None = None,
    cells: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    masses: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    """Construct a valid synthetic trajectory from Cartesian coordinates."""
    positions = np.asarray(cartesian_positions, dtype=np.float64)
    n_frames, n_atoms, _ = positions.shape
    if times is None:
        times = np.arange(n_frames, dtype=np.float64) * 0.1
    else:
        times = np.asarray(times, dtype=np.float64)
    if cells is None:
        cells = np.repeat(
            np.eye(3, dtype=np.float64)[None, :, :] * 10.0, n_frames, axis=0
        )
    else:
        cells = np.asarray(cells, dtype=np.float64)
    if atomic_numbers is None:
        atomic_numbers = np.ones(n_atoms, dtype=np.int32)
    if masses is None:
        masses = np.ones(n_atoms, dtype=np.float64)

    inverse_cells = np.linalg.inv(cells)
    scaled = np.einsum("tni,tij->tnj", positions, inverse_cells, optimize=True)
    velocities = np.gradient(positions, times, axis=0, edge_order=1)

    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.asarray(masses, dtype=np.float64),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames, dtype=np.int64) * 10,
        times=times,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=scaled,
        velocities=velocities,
        provenance=FrameCollectionProvenance(
            source_format="lammps-custom-dump",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_static_trajectory_has_zero_msd() -> None:
    positions = np.zeros((6, 3, 3), dtype=np.float64)
    trajectory = make_trajectory(positions)

    result = compute_msd(trajectory)

    np.testing.assert_array_equal(result.msd, 0.0)
    np.testing.assert_array_equal(result.components, 0.0)
    np.testing.assert_array_equal(result.tensor, 0.0)


def test_constant_velocity_fixed_origin_is_exact() -> None:
    times = np.arange(6, dtype=np.float64) * 0.2
    velocity = np.array([2.0, -1.0, 0.5])
    positions = times[:, None, None] * velocity[None, None, :]
    positions = np.repeat(positions, 2, axis=1)
    trajectory = make_trajectory(positions, times=times)

    with pytest.warns(FixedOriginMSDWarning):
        result = compute_msd(
            trajectory,
            mode="fixed_origin",
            per_atom=True,
        )

    expected_components = result.lag_times[:, None] ** 2 * velocity[None, :] ** 2
    np.testing.assert_allclose(result.components, expected_components)
    np.testing.assert_allclose(result.msd, np.sum(expected_components, axis=1))
    np.testing.assert_allclose(
        result.per_atom_msd,
        np.repeat(result.msd[:, None], 2, axis=1),
    )
    np.testing.assert_array_equal(result.n_origins, 1)


def test_constant_velocity_time_average_is_exact() -> None:
    times = np.arange(8, dtype=np.float64) * 0.1
    velocity = np.array([1.5, 0.0, -0.5])
    positions = times[:, None, None] * velocity[None, None, :]
    positions = np.repeat(positions, 4, axis=1)
    trajectory = make_trajectory(positions, times=times)

    result = compute_msd(trajectory, max_lag=5, origin_stride=2)

    expected = result.lag_times**2 * np.dot(velocity, velocity)
    np.testing.assert_allclose(result.msd, expected)
    np.testing.assert_array_equal(result.n_origins, [4, 4, 3, 3, 2, 2])


def test_tensor_trace_and_components_are_consistent() -> None:
    positions = np.zeros((5, 2, 3), dtype=np.float64)
    positions[:, 0, 0] = np.arange(5)
    positions[:, 1, 1] = 2.0 * np.arange(5)
    trajectory = make_trajectory(positions)

    result = compute_msd(trajectory, max_lag=4, per_atom=True)

    np.testing.assert_allclose(result.msd, np.trace(result.tensor, axis1=1, axis2=2))
    np.testing.assert_allclose(
        result.components, np.diagonal(result.tensor, axis1=1, axis2=2)
    )
    np.testing.assert_allclose(result.msd, np.mean(result.per_atom_msd, axis=1))


def test_species_and_explicit_index_selection() -> None:
    positions = np.zeros((4, 3, 3), dtype=np.float64)
    positions[:, 0, 0] = np.arange(4)
    positions[:, 1, 0] = 2.0 * np.arange(4)
    positions[:, 2, 0] = 3.0 * np.arange(4)
    trajectory = make_trajectory(
        positions,
        atomic_numbers=np.array([11, 8, 11]),
        masses=np.array([22.99, 16.0, 22.99]),
    )

    sodium = compute_msd(trajectory, species="Na", max_lag=1, per_atom=True)
    explicit = compute_msd(trajectory, atom_indices=[2, 0], max_lag=1, per_atom=True)

    np.testing.assert_array_equal(sodium.atom_indices, [0, 2])
    np.testing.assert_array_equal(explicit.atom_indices, [2, 0])
    np.testing.assert_allclose(sodium.msd, explicit.msd)
    np.testing.assert_allclose(sodium.per_atom_msd[:, ::-1], explicit.per_atom_msd)


def test_center_of_mass_drift_removes_uniform_translation() -> None:
    times = np.arange(6, dtype=np.float64) * 0.1
    positions = np.zeros((6, 2, 3), dtype=np.float64)
    positions[:, :, 0] = times[:, None] * 3.0
    trajectory = make_trajectory(positions, times=times, masses=np.array([1.0, 3.0]))

    uncorrected = compute_msd(trajectory, max_lag=3)
    corrected = compute_msd(
        trajectory,
        max_lag=3,
        drift_mode="center_of_mass",
    )

    assert uncorrected.msd[-1] > 0.0
    np.testing.assert_allclose(corrected.msd, 0.0, atol=1e-28)


def test_subset_drift_warning_and_relative_motion() -> None:
    positions = np.zeros((5, 3, 3), dtype=np.float64)
    positions[:, 0, 0] = np.arange(5)
    positions[:, 1, 0] = np.arange(5)
    trajectory = make_trajectory(positions)

    with pytest.warns(CollectiveMotionWarning):
        result = compute_msd(
            trajectory,
            atom_indices=[0, 1],
            drift_mode="center_of_geometry",
            drift_atom_indices=[0, 1],
            max_lag=2,
        )

    np.testing.assert_allclose(result.msd, 0.0)


def test_variable_cell_laboratory_and_reference_modes_differ() -> None:
    n_frames = 5
    cells = np.zeros((n_frames, 3, 3), dtype=np.float64)
    for frame, length in enumerate(np.linspace(10.0, 12.0, n_frames)):
        cells[frame] = np.eye(3) * length
    scaled = np.full((n_frames, 1, 3), 0.5)
    positions = np.einsum("tni,tij->tnj", scaled, cells)
    trajectory = make_trajectory(positions, cells=cells)

    with pytest.warns((VariableCellMSDWarning, FixedOriginMSDWarning)):
        laboratory = compute_msd(trajectory, mode="fixed_origin")
    with pytest.warns(FixedOriginMSDWarning):
        reference = compute_msd(
            trajectory,
            mode="fixed_origin",
            coordinate_mode="reference_cell",
            reference_cell="initial",
        )

    assert laboratory.msd[-1] > 0.0
    np.testing.assert_allclose(reference.msd, 0.0, atol=1e-28)
    np.testing.assert_allclose(reference.reference_cell, cells[0])


def test_nonuniform_time_grid_is_rejected() -> None:
    positions = np.zeros((4, 1, 3), dtype=np.float64)
    trajectory = make_trajectory(positions, times=np.array([0.0, 0.1, 0.25, 0.35]))

    with pytest.raises(ValueError, match="uniformly sampled"):
        compute_msd(trajectory)


def test_invalid_selections_and_lags_are_rejected() -> None:
    trajectory = make_trajectory(np.zeros((4, 2, 3), dtype=np.float64))

    with pytest.raises(ValueError, match="mutually exclusive"):
        compute_msd(trajectory, species="H", atom_indices=[0])
    with pytest.raises(ValueError, match="duplicate"):
        compute_msd(trajectory, atom_indices=[0, 0])
    with pytest.raises(IndexError, match="outside"):
        compute_msd(trajectory, atom_indices=[2])
    with pytest.raises(ValueError, match="exceeds"):
        compute_msd(trajectory, max_lag=4)


def test_compute_tensor_false_omits_only_full_tensor() -> None:
    positions = np.zeros((4, 1, 3), dtype=np.float64)
    positions[:, 0, 2] = np.arange(4)
    trajectory = make_trajectory(positions)

    result = compute_msd(trajectory, compute_tensor=False, max_lag=2)

    assert result.tensor is None
    np.testing.assert_allclose(result.msd, np.sum(result.components, axis=1))


def test_fixed_origin_preserves_nonstationary_transition_history() -> None:
    positions = np.zeros((6, 1, 3), dtype=np.float64)
    positions[:, 0, 0] = [0.0, 0.0, 0.0, 1.0, 3.0, 6.0]
    trajectory = make_trajectory(positions)

    with pytest.warns(FixedOriginMSDWarning):
        fixed = compute_msd(
            trajectory,
            mode="fixed_origin",
            origin_frame=1,
            max_lag=4,
        )
    averaged = compute_msd(trajectory, mode="time_averaged", max_lag=4)

    np.testing.assert_allclose(fixed.msd, [0.0, 0.0, 1.0, 9.0, 36.0])
    assert not np.allclose(fixed.msd, averaged.msd)
    assert fixed.metadata["origin_frame"] == 1
    assert fixed.metadata["origin_step"] == 10


@pytest.mark.parametrize("n_frames", [65, 66, 127])
def test_fft_matches_direct_for_random_walk(n_frames: int) -> None:
    rng = np.random.default_rng(1234 + n_frames)
    positions = np.cumsum(
        rng.normal(scale=0.05, size=(n_frames, 7, 3)),
        axis=0,
    )
    trajectory = make_trajectory(positions)

    direct = compute_msd(
        trajectory,
        max_lag=min(31, n_frames // 2),
        backend="direct",
        per_atom=True,
    )
    fft = compute_msd(
        trajectory,
        max_lag=min(31, n_frames // 2),
        backend="fft",
        atom_block_size=3,
        per_atom=True,
    )

    np.testing.assert_allclose(fft.msd, direct.msd, rtol=2e-12, atol=2e-13)
    np.testing.assert_allclose(
        fft.components, direct.components, rtol=2e-12, atol=2e-13
    )
    np.testing.assert_allclose(fft.tensor, direct.tensor, rtol=2e-12, atol=2e-13)
    np.testing.assert_allclose(
        fft.per_atom_msd, direct.per_atom_msd, rtol=2e-12, atol=2e-13
    )
    np.testing.assert_array_equal(fft.n_origins, direct.n_origins)
    assert fft.metadata["chosen_backend"] == "fft"
    assert fft.metadata["atom_block_size"] == 3
    assert fft.metadata["fft_length"] >= 2 * n_frames - 1


def test_fft_matches_direct_without_full_tensor() -> None:
    rng = np.random.default_rng(55)
    positions = np.cumsum(rng.normal(size=(96, 5, 3)), axis=0)
    trajectory = make_trajectory(positions)

    direct = compute_msd(
        trajectory,
        max_lag=37,
        lag_stride=3,
        compute_tensor=False,
        backend="direct",
    )
    fft = compute_msd(
        trajectory,
        max_lag=37,
        lag_stride=3,
        compute_tensor=False,
        backend="fft",
        atom_block_size=2,
    )

    assert fft.tensor is None
    np.testing.assert_allclose(fft.msd, direct.msd, rtol=2e-12, atol=2e-12)
    np.testing.assert_allclose(
        fft.components, direct.components, rtol=2e-12, atol=2e-12
    )


def test_fft_matches_direct_with_reference_cell_and_drift() -> None:
    rng = np.random.default_rng(77)
    n_frames = 80
    cells = np.empty((n_frames, 3, 3), dtype=np.float64)
    for frame, scale in enumerate(np.linspace(0.98, 1.02, n_frames)):
        cells[frame] = np.array(
            [[10.0 * scale, 0.0, 0.0], [0.2, 11.0 * scale, 0.0], [0.1, 0.3, 9.0]],
            dtype=np.float64,
        )
    scaled = np.cumsum(rng.normal(scale=0.002, size=(n_frames, 6, 3)), axis=0)
    scaled += np.array([0.2, 0.3, 0.4])
    positions = np.einsum("tni,tij->tnj", scaled, cells)
    trajectory = make_trajectory(
        positions,
        cells=cells,
        masses=np.array([1.0, 2.0, 3.0, 1.5, 2.5, 4.0]),
    )

    kwargs = dict(
        max_lag=29,
        coordinate_mode="reference_cell",
        reference_cell="mean",
        drift_mode="center_of_mass",
        drift_atom_indices=[0, 1, 2],
    )
    direct = compute_msd(trajectory, backend="direct", **kwargs)
    fft = compute_msd(trajectory, backend="fft", atom_block_size=2, **kwargs)

    np.testing.assert_allclose(fft.msd, direct.msd, rtol=5e-12, atol=5e-14)
    np.testing.assert_allclose(fft.tensor, direct.tensor, rtol=5e-12, atol=5e-14)


def test_fft_coordinate_centering_handles_large_absolute_positions() -> None:
    n_frames = 128
    offsets = np.full((n_frames, 3, 3), 1.0e12, dtype=np.float64)
    increments = np.arange(n_frames, dtype=np.float64)[:, None, None] * 1.0e-4
    positions = offsets + increments * np.array([[[1.0, 2.0, 3.0]]])
    trajectory = make_trajectory(positions)

    direct = compute_msd(trajectory, max_lag=40, backend="direct")
    fft = compute_msd(trajectory, max_lag=40, backend="fft")

    np.testing.assert_allclose(fft.msd, direct.msd, rtol=2e-12, atol=2e-15)
    assert fft.metadata["fft_coordinate_centering"] == (
        "subtract_first_position_per_atom"
    )


def test_fft_rejects_sparse_origins_and_fixed_origin_mode() -> None:
    trajectory = make_trajectory(np.zeros((80, 2, 3), dtype=np.float64))

    with pytest.raises(ValueError, match="origin_stride == 1"):
        compute_msd(trajectory, backend="fft", origin_stride=2)
    with pytest.raises(ValueError, match="not applicable to fixed-origin"):
        compute_msd(trajectory, mode="fixed_origin", backend="fft")


def test_auto_backend_selects_fft_for_long_expensive_trajectory() -> None:
    rng = np.random.default_rng(123)
    positions = np.cumsum(rng.normal(scale=0.01, size=(512, 24, 3)), axis=0)
    trajectory = make_trajectory(positions)

    result = compute_msd(
        trajectory,
        max_lag=256,
        backend="auto",
        compute_tensor=True,
    )

    assert result.metadata["chosen_backend"] == "fft"
    assert result.metadata["fft_length"] is not None
