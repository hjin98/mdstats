"""Focused D1-D2 displacement-dynamics tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    SelfVanHoveResult,
    compute_msd,
    compute_self_van_hove,
)


def make_trajectory(
    positions: np.ndarray,
    *,
    times: np.ndarray | None = None,
    cells: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    masses: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    cartesian = np.asarray(positions, dtype=np.float64)
    n_frames, n_atoms, _ = cartesian.shape
    if times is None:
        times = np.arange(n_frames, dtype=np.float64) * 0.2
    else:
        times = np.asarray(times, dtype=np.float64)
    if cells is None:
        cells = np.repeat((20.0 * np.eye(3))[None, :, :], n_frames, axis=0)
    else:
        cells = np.asarray(cells, dtype=np.float64)
    if atomic_numbers is None:
        atomic_numbers = np.arange(1, n_atoms + 1, dtype=np.int32)
    if masses is None:
        masses = np.arange(1, n_atoms + 1, dtype=np.float64)
    fractional = np.einsum(
        "tni,tij->tnj",
        cartesian,
        np.linalg.inv(cells),
        optimize=True,
    )
    velocities = np.gradient(cartesian, times, axis=0, edge_order=1)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.asarray(masses, dtype=np.float64),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames, dtype=np.int64),
        times=times,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=velocities,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("d1-test",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_static_atoms_auto_support_is_finite_and_complete() -> None:
    trajectory = make_trajectory(np.zeros((6, 2, 3), dtype=np.float64))
    result = compute_self_van_hove(
        trajectory,
        lag_steps=[0, 1, 3],
        n_bins=8,
    )

    assert isinstance(result, SelfVanHoveResult)
    assert result.radial_edges[-1] > 0.0
    np.testing.assert_array_equal(result.overflow_counts, 0)
    np.testing.assert_allclose(result.direct_second_moment, 0.0, atol=0.0)
    np.testing.assert_array_equal(result.counts[:, 0], result.n_samples)
    np.testing.assert_array_equal(result.counts[:, 1:], 0)
    np.testing.assert_allclose(
        np.sum(result.density * result.shell_measure[None, :], axis=1),
        1.0,
    )
    assert result.metadata["radial_support_mode"] == "automatic_complete"


def test_final_edge_is_inclusive_and_value_above_overflows() -> None:
    positions = np.zeros((3, 1, 3), dtype=np.float64)
    positions[:, 0, 0] = [0.0, 1.0, 2.0]
    trajectory = make_trajectory(positions)

    inclusive = compute_self_van_hove(
        trajectory,
        lag_steps=[1],
        radial_edges=[0.0, 0.5, 1.0],
    )
    np.testing.assert_array_equal(inclusive.counts, [[0, 2]])
    np.testing.assert_array_equal(inclusive.overflow_counts, [0])

    below_one = float(np.nextafter(1.0, 0.0))
    overflow = compute_self_van_hove(
        trajectory,
        lag_steps=[1],
        radial_edges=[0.0, 0.5, below_one],
    )
    np.testing.assert_array_equal(overflow.counts, [[0, 0]])
    np.testing.assert_array_equal(overflow.overflow_counts, [2])
    np.testing.assert_allclose(overflow.overflow_probability, [1.0])
    np.testing.assert_allclose(overflow.captured_probability, [0.0])

    with pytest.raises(ValueError, match="excluded 2 displacement samples"):
        compute_self_van_hove(
            trajectory,
            lag_steps=[1],
            radial_edges=[0.0, 0.5, below_one],
            require_complete_support=True,
        )


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_dimension_correct_shell_measures(rank: int) -> None:
    trajectory = make_trajectory(np.zeros((2, 1, 3), dtype=np.float64))
    axes = ("x", "y", "z")[:rank]
    result = compute_self_van_hove(
        trajectory,
        lag_steps=[0],
        radial_edges=[0.0, 1.0, 2.0],
        axes=axes,
    )
    if rank == 1:
        expected = np.array([2.0, 2.0])
    elif rank == 2:
        expected = np.pi * np.array([1.0, 3.0])
    else:
        expected = (4.0 * np.pi / 3.0) * np.array([1.0, 7.0])
    np.testing.assert_allclose(result.shell_measure, expected)
    assert result.metadata["density_units"] == f"angstrom^-{rank}"


def test_projected_translation_and_rotated_basis() -> None:
    times = np.arange(5, dtype=np.float64) * 0.25
    velocity = np.array([2.0, -1.0, 3.0])
    positions = times[:, None, None] * velocity[None, None, :]
    trajectory = make_trajectory(positions, times=times)
    direction = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)

    result = compute_self_van_hove(
        trajectory,
        lag_steps=[0, 2],
        projection_basis=direction,
        r_max=1.0,
        n_bins=20,
    )
    expected_radius = abs(float(np.dot(2.0 * 0.25 * velocity, direction)))
    np.testing.assert_allclose(
        result.direct_second_moment,
        [0.0, expected_radius**2],
        rtol=1.0e-14,
        atol=1.0e-14,
    )
    assert result.projection_basis.shape == (1, 3)
    np.testing.assert_array_equal(result.signature.projection_basis, result.projection_basis)


def test_direct_second_moment_matches_direct_msd() -> None:
    rng = np.random.default_rng(9401)
    increments = rng.normal(scale=0.1, size=(11, 3, 3))
    positions = np.concatenate(
        [np.zeros((1, 3, 3)), np.cumsum(increments, axis=0)],
        axis=0,
    )
    trajectory = make_trajectory(positions)
    van_hove = compute_self_van_hove(
        trajectory,
        lag_steps=[0, 1, 2, 3],
        origin_stride=2,
        n_bins=60,
    )
    msd = compute_msd(
        trajectory,
        mode="time_averaged",
        max_lag=3,
        origin_stride=2,
        backend="direct",
    )
    np.testing.assert_allclose(
        van_hove.direct_second_moment,
        msd.msd,
        rtol=2.0e-15,
        atol=2.0e-15,
    )
    np.testing.assert_array_equal(
        van_hove.n_samples,
        msd.n_origins * trajectory.n_atoms,
    )


def test_explicit_atom_order_and_block_invariance() -> None:
    rng = np.random.default_rng(401)
    positions = np.cumsum(rng.normal(size=(9, 4, 3)), axis=0)
    trajectory = make_trajectory(positions)
    kwargs = dict(
        atom_indices=[3, 0, 2],
        lag_steps=[0, 1, 4],
        origin_stride=2,
        radial_edges=np.linspace(0.0, 8.0, 33),
    )
    small = compute_self_van_hove(
        trajectory,
        atom_block_size=1,
        origin_block_size=1,
        **kwargs,
    )
    broad = compute_self_van_hove(
        trajectory,
        atom_block_size=3,
        origin_block_size=9,
        **kwargs,
    )
    np.testing.assert_array_equal(small.atom_indices, [3, 0, 2])
    np.testing.assert_array_equal(small.counts, broad.counts)
    np.testing.assert_array_equal(small.overflow_counts, broad.overflow_counts)
    np.testing.assert_array_equal(small.n_samples, broad.n_samples)
    np.testing.assert_allclose(
        small.direct_second_moment,
        broad.direct_second_moment,
        rtol=2.0e-15,
        atol=2.0e-15,
    )
    np.testing.assert_allclose(small.density, broad.density, rtol=0.0, atol=0.0)


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_seeded_gaussian_increment_second_moment(rank: int) -> None:
    rng = np.random.default_rng(1800 + rank)
    sigma = 0.3
    increments = rng.normal(scale=sigma, size=(6000, 1, 3))
    positions = np.concatenate(
        [np.zeros((1, 1, 3)), np.cumsum(increments, axis=0)],
        axis=0,
    )
    trajectory = make_trajectory(positions)
    axes = ("x", "y", "z")[:rank]
    result = compute_self_van_hove(
        trajectory,
        lag_steps=[1],
        axes=axes,
        n_bins=100,
    )
    assert result.overflow_counts[0] == 0
    assert result.direct_second_moment[0] == pytest.approx(
        rank * sigma**2,
        rel=0.04,
    )
    np.testing.assert_allclose(
        np.sum(result.density[0] * result.shell_measure),
        1.0,
        rtol=1.0e-14,
        atol=1.0e-14,
    )


def test_probability_uses_total_samples_not_captured_samples() -> None:
    positions = np.zeros((4, 1, 3), dtype=np.float64)
    positions[:, 0, 0] = [0.0, 0.25, 1.0, 2.0]
    trajectory = make_trajectory(positions)
    result = compute_self_van_hove(
        trajectory,
        lag_steps=[1],
        radial_edges=[0.0, 0.5],
    )
    # Lag-one radii are 0.25, 0.75, and 1.0: one captured, two overflow.
    np.testing.assert_array_equal(result.counts, [[1]])
    np.testing.assert_array_equal(result.overflow_counts, [2])
    np.testing.assert_allclose(result.shell_probability, [[1.0 / 3.0]])
    np.testing.assert_allclose(result.overflow_probability, [2.0 / 3.0])
    np.testing.assert_allclose(
        np.sum(result.density * result.shell_measure[None, :], axis=1),
        result.captured_probability,
    )


def test_result_is_deeply_immutable_and_exported() -> None:
    trajectory = make_trajectory(np.zeros((3, 1, 3), dtype=np.float64))
    result = compute_self_van_hove(trajectory, lag_steps=[0, 1], n_bins=4)
    import mdstats
    import mdstats.analysis

    assert mdstats.SelfVanHoveResult is SelfVanHoveResult
    assert mdstats.analysis.SelfVanHoveResult is SelfVanHoveResult
    assert mdstats.compute_self_van_hove is compute_self_van_hove
    assert mdstats.analysis.compute_self_van_hove is compute_self_van_hove
    for array in (
        result.lag_steps,
        result.lag_times,
        result.radial_edges,
        result.radial_centers,
        result.shell_measure,
        result.shell_probability,
        result.density,
        result.counts,
        result.overflow_counts,
        result.overflow_probability,
        result.n_samples,
        result.direct_second_moment,
        result.atom_indices,
        result.projection_basis,
        result.captured_probability,
    ):
        with pytest.raises(ValueError):
            array.flat[0] = 1
    with pytest.raises(TypeError):
        result.metadata["new"] = 1
    with pytest.raises(TypeError):
        result.metadata["input"]["new"] = 1


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"lag_steps": [1], "max_lag": 1}, ValueError),
        ({"lag_steps": [1.0]}, TypeError),
        ({"lag_steps": [True]}, TypeError),
        ({"lag_steps": [2, 1]}, ValueError),
        ({"max_lag": True}, TypeError),
        ({"origin_stride": True}, TypeError),
        ({"n_bins": True}, TypeError),
        ({"n_bins": 0}, ValueError),
        ({"radial_edges": [0.1, 1.0]}, ValueError),
        ({"radial_edges": [0.0, 1.0, 1.0]}, ValueError),
        ({"radial_edges": [0.0, np.inf]}, ValueError),
        ({"radial_edges": [0.0, 1.0], "r_max": 1.0}, ValueError),
        ({"r_max": 0.0}, ValueError),
        ({"require_complete_support": 1}, TypeError),
        ({"atom_block_size": False}, TypeError),
        ({"origin_block_size": 0}, ValueError),
        ({"axes": ("x",), "projection_basis": [[1.0, 0.0, 0.0]]}, ValueError),
    ],
)
def test_invalid_inputs_are_rejected(kwargs: dict[str, object], error: type[Exception]) -> None:
    trajectory = make_trajectory(np.zeros((4, 1, 3), dtype=np.float64))
    with pytest.raises(error):
        compute_self_van_hove(trajectory, **kwargs)


def test_default_lags_match_half_record_many_origin_window() -> None:
    positions = np.zeros((9, 1, 3), dtype=np.float64)
    positions[:, 0, 0] = np.arange(9, dtype=np.float64)
    trajectory = make_trajectory(positions)
    result = compute_self_van_hove(trajectory, n_bins=12)
    np.testing.assert_array_equal(result.lag_steps, np.arange(5))
    np.testing.assert_array_equal(result.n_samples, [9, 8, 7, 6, 5])
    assert result.metadata["support_complete"] is True
    assert result.metadata["maximum_observed_radius_angstrom"] < result.radial_edges[-1]


def test_reference_cell_drift_and_projection_are_preserved_in_signature() -> None:
    n_frames = 6
    cells = np.repeat(np.eye(3)[None, :, :], n_frames, axis=0)
    cells[:, 0, 0] = np.linspace(10.0, 12.0, n_frames)
    fractional = np.zeros((n_frames, 2, 3), dtype=np.float64)
    fractional[:, 0, 0] = 0.2
    fractional[:, 1, 0] = 0.4
    positions = np.einsum("tni,tij->tnj", fractional, cells)
    positions += np.arange(n_frames)[:, None, None] * np.array([0.5, -0.2, 0.0])
    trajectory = make_trajectory(
        positions,
        cells=cells,
        atomic_numbers=np.array([3, 11]),
        masses=np.array([1.0, 3.0]),
    )
    result = compute_self_van_hove(
        trajectory,
        atom_indices=[1],
        lag_steps=[0, 1, 2],
        coordinate_mode="reference_cell",
        reference_cell="initial",
        drift_mode="center_of_mass",
        drift_atom_indices=[0, 1],
        axes=("x",),
        n_bins=16,
    )
    assert result.signature.coordinate_mode == "reference_cell"
    assert result.signature.reference_cell_mode == "initial"
    assert result.signature.drift_mode == "center_of_mass"
    np.testing.assert_array_equal(result.signature.drift_atom_indices, [0, 1])
    np.testing.assert_array_equal(result.atom_indices, [1])
    assert result.signature.projection_labels == ("x",)
    np.testing.assert_array_equal(result.projection_basis, [[1.0, 0.0, 0.0]])


def test_d1_module_specification_has_pdf_companion() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    stem = root / "docs" / "specs" / "analysis" / "displacement_dynamics_spec"
    assert stem.with_suffix(".md").is_file()
    assert stem.with_suffix(".pdf").is_file()


# D2 non-Gaussian parameter tests.


def test_non_gaussian_static_trajectory_is_undefined_at_every_lag() -> None:
    from mdstats import NonGaussianResult, compute_non_gaussian_parameter

    trajectory = make_trajectory(np.zeros((7, 2, 3), dtype=np.float64))
    result = compute_non_gaussian_parameter(trajectory, max_lag=3)
    assert isinstance(result, NonGaussianResult)
    np.testing.assert_array_equal(result.lag_steps, [0, 1, 2, 3])
    np.testing.assert_allclose(result.second_moment, 0.0, atol=0.0)
    np.testing.assert_allclose(result.fourth_moment, 0.0, atol=0.0)
    np.testing.assert_array_equal(result.undefined_mask, True)
    assert np.all(np.isnan(result.alpha2))
    assert result.metadata["undefined_lag_count"] == 4


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_non_gaussian_fixed_radius_translation_has_exact_dimension_value(
    rank: int,
) -> None:
    from mdstats import compute_non_gaussian_parameter

    times = np.arange(8, dtype=np.float64) * 0.25
    velocity = np.array([1.0, -2.0, 0.5])
    positions = times[:, None, None] * velocity[None, None, :]
    trajectory = make_trajectory(positions, times=times)
    axes = ("x", "y", "z")[:rank]
    result = compute_non_gaussian_parameter(
        trajectory,
        max_lag=2,
        axes=axes,
    )
    assert result.undefined_mask[0]
    np.testing.assert_allclose(
        result.alpha2[1:],
        -2.0 / (rank + 2.0),
        rtol=2.0e-14,
        atol=2.0e-14,
    )


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_non_gaussian_seeded_gaussian_increments_are_near_zero(rank: int) -> None:
    from mdstats import compute_non_gaussian_parameter

    rng = np.random.default_rng(7200 + rank)
    increments = rng.normal(scale=0.35, size=(12000, 1, 3))
    positions = np.concatenate(
        [np.zeros((1, 1, 3)), np.cumsum(increments, axis=0)],
        axis=0,
    )
    trajectory = make_trajectory(positions)
    result = compute_non_gaussian_parameter(
        trajectory,
        max_lag=1,
        axes=("x", "y", "z")[:rank],
    )
    assert result.undefined_mask[0]
    assert not result.undefined_mask[1]
    assert result.alpha2[1] == pytest.approx(0.0, abs=0.045)


def test_non_gaussian_two_population_scale_mixture_is_positive() -> None:
    from mdstats import compute_non_gaussian_parameter

    n_frames = 40
    positions = np.zeros((n_frames, 10, 3), dtype=np.float64)
    positions[:, 9, 0] = 10.0 * np.arange(n_frames, dtype=np.float64)
    trajectory = make_trajectory(positions)
    result = compute_non_gaussian_parameter(
        trajectory,
        max_lag=1,
        axes=("x",),
    )
    assert result.alpha2[1] > 2.0


def test_non_gaussian_later_zero_lag_is_undefined() -> None:
    from mdstats import compute_non_gaussian_parameter

    positions = np.zeros((3, 1, 3), dtype=np.float64)
    positions[:, 0, 0] = [0.0, 1.0, 0.0]
    trajectory = make_trajectory(positions)
    result = compute_non_gaussian_parameter(
        trajectory,
        max_lag=2,
        axes=("x",),
    )
    np.testing.assert_array_equal(result.undefined_mask, [True, False, True])
    assert np.isnan(result.alpha2[0])
    assert np.isfinite(result.alpha2[1])
    assert np.isnan(result.alpha2[2])


def test_non_gaussian_second_moment_matches_d1_and_direct_msd() -> None:
    from mdstats import compute_non_gaussian_parameter

    rng = np.random.default_rng(9012)
    increments = rng.normal(scale=0.2, size=(13, 3, 3))
    positions = np.concatenate(
        [np.zeros((1, 3, 3)), np.cumsum(increments, axis=0)],
        axis=0,
    )
    trajectory = make_trajectory(positions)
    ngp = compute_non_gaussian_parameter(
        trajectory,
        max_lag=4,
        lag_stride=2,
        origin_stride=2,
    )
    van_hove = compute_self_van_hove(
        trajectory,
        lag_steps=[0, 2, 4],
        origin_stride=2,
        n_bins=50,
    )
    msd = compute_msd(
        trajectory,
        mode="time_averaged",
        max_lag=4,
        lag_stride=2,
        origin_stride=2,
        backend="direct",
    )
    np.testing.assert_allclose(
        ngp.second_moment,
        van_hove.direct_second_moment,
        rtol=2.0e-15,
        atol=2.0e-15,
    )
    np.testing.assert_allclose(
        ngp.second_moment,
        msd.msd,
        rtol=2.0e-15,
        atol=2.0e-15,
    )
    np.testing.assert_array_equal(ngp.n_samples, msd.n_origins * trajectory.n_atoms)


def test_non_gaussian_rotated_projection_uses_rank_one_prefactor() -> None:
    from mdstats import compute_non_gaussian_parameter

    positions = np.zeros((5, 2, 3), dtype=np.float64)
    direction = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    positions[:, 0, :] = np.arange(5)[:, None] * direction[None, :]
    positions[:, 1, :] = 2.0 * np.arange(5)[:, None] * direction[None, :]
    trajectory = make_trajectory(positions)
    result = compute_non_gaussian_parameter(
        trajectory,
        max_lag=1,
        projection_basis=direction,
    )
    m2 = (1.0**2 + 2.0**2) / 2.0
    m4 = (1.0**4 + 2.0**4) / 2.0
    expected = (1.0 / 3.0) * m4 / (m2 * m2) - 1.0
    assert result.second_moment[1] == pytest.approx(m2)
    assert result.fourth_moment[1] == pytest.approx(m4)
    assert result.alpha2[1] == pytest.approx(expected)
    assert result.metadata["subspace_rank"] == 1


def test_non_gaussian_block_invariance_and_atom_order() -> None:
    from mdstats import compute_non_gaussian_parameter

    rng = np.random.default_rng(551)
    positions = np.cumsum(rng.normal(size=(12, 5, 3)), axis=0)
    trajectory = make_trajectory(positions)
    kwargs = dict(
        atom_indices=[4, 1, 3],
        max_lag=4,
        lag_stride=2,
        origin_stride=2,
    )
    small = compute_non_gaussian_parameter(
        trajectory,
        atom_block_size=1,
        origin_block_size=1,
        **kwargs,
    )
    broad = compute_non_gaussian_parameter(
        trajectory,
        atom_block_size=3,
        origin_block_size=12,
        **kwargs,
    )
    np.testing.assert_array_equal(small.atom_indices, [4, 1, 3])
    np.testing.assert_array_equal(small.n_samples, broad.n_samples)
    np.testing.assert_allclose(small.second_moment, broad.second_moment, rtol=2e-15, atol=2e-15)
    np.testing.assert_allclose(small.fourth_moment, broad.fourth_moment, rtol=3e-15, atol=3e-15)
    np.testing.assert_allclose(small.alpha2, broad.alpha2, rtol=3e-15, atol=3e-15, equal_nan=True)


def test_non_gaussian_result_is_deeply_immutable_and_exported() -> None:
    import mdstats
    import mdstats.analysis
    from mdstats import NonGaussianResult, compute_non_gaussian_parameter

    trajectory = make_trajectory(np.zeros((4, 1, 3), dtype=np.float64))
    result = compute_non_gaussian_parameter(trajectory, max_lag=1)
    assert mdstats.NonGaussianResult is NonGaussianResult
    assert mdstats.analysis.NonGaussianResult is NonGaussianResult
    assert mdstats.compute_non_gaussian_parameter is compute_non_gaussian_parameter
    assert mdstats.analysis.compute_non_gaussian_parameter is compute_non_gaussian_parameter
    for array in (
        result.lag_steps,
        result.lag_times,
        result.second_moment,
        result.fourth_moment,
        result.alpha2,
        result.undefined_mask,
        result.n_samples,
        result.atom_indices,
        result.projection_basis,
    ):
        with pytest.raises(ValueError):
            array.flat[0] = 1
    with pytest.raises(TypeError):
        result.metadata["new"] = 1
    with pytest.raises(TypeError):
        result.metadata["input"]["new"] = 1


def test_non_gaussian_constructor_rejects_inconsistent_derived_fields() -> None:
    from dataclasses import replace
    from mdstats import compute_non_gaussian_parameter

    positions = np.zeros((4, 1, 3), dtype=np.float64)
    positions[:, 0, 0] = np.arange(4, dtype=np.float64)
    trajectory = make_trajectory(positions)
    result = compute_non_gaussian_parameter(trajectory, max_lag=1, axes=("x",))
    bad_alpha = np.array(result.alpha2, copy=True)
    bad_alpha[1] += 0.1
    with pytest.raises(ValueError, match="inconsistent"):
        replace(result, alpha2=bad_alpha)
    bad_mask = np.array(result.undefined_mask, copy=True)
    bad_mask[1] = True
    with pytest.raises(ValueError, match="undefined_mask"):
        replace(result, undefined_mask=bad_mask)


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"max_lag": True}, TypeError),
        ({"max_lag": -1}, ValueError),
        ({"max_lag": 4}, ValueError),
        ({"origin_stride": True}, TypeError),
        ({"origin_stride": 0}, ValueError),
        ({"lag_stride": False}, TypeError),
        ({"lag_stride": 0}, ValueError),
        ({"atom_block_size": False}, TypeError),
        ({"origin_block_size": 0}, ValueError),
        ({"axes": ("x",), "projection_basis": [[1.0, 0.0, 0.0]]}, ValueError),
    ],
)
def test_non_gaussian_invalid_inputs_are_rejected(
    kwargs: dict[str, object],
    error: type[Exception],
) -> None:
    from mdstats import compute_non_gaussian_parameter

    trajectory = make_trajectory(np.zeros((4, 1, 3), dtype=np.float64))
    with pytest.raises(error):
        compute_non_gaussian_parameter(trajectory, **kwargs)

# D3 self-intermediate scattering tests
from scipy.special import j0 as scipy_j0, spherical_jn as scipy_spherical_jn

from mdstats import (
    SelfIntermediateScatteringResult,
    compute_self_intermediate_scattering,
)


def test_scattering_ballistic_explicit_vectors_and_q_order() -> None:
    times = np.arange(7, dtype=np.float64) * 0.2
    velocity = np.array([0.7, -0.4, 0.2])
    positions = times[:, None, None] * velocity[None, None, :]
    trajectory = make_trajectory(positions, times=times)
    q = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.2, -0.3, 0.5],
            [-1.2, 0.3, -0.5],
            [1.2, -0.3, 0.5],
        ]
    )
    result = compute_self_intermediate_scattering(
        trajectory,
        q_vectors=q,
        isotropic=False,
        max_lag=3,
    )
    assert isinstance(result, SelfIntermediateScatteringResult)
    np.testing.assert_array_equal(result.q_vectors, q)
    expected_phase = np.outer(result.lag_times, q @ velocity)
    np.testing.assert_allclose(
        result.values,
        np.exp(1j * expected_phase),
        rtol=3.0e-15,
        atol=3.0e-15,
    )
    np.testing.assert_array_equal(result.values[:, 0], 1.0 + 0.0j)
    np.testing.assert_allclose(result.values[:, 2], np.conjugate(result.values[:, 1]))
    np.testing.assert_array_equal(result.values[:, 1], result.values[:, 3])
    assert not result.isotropic


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_scattering_dimension_correct_isotropic_kernels(rank: int) -> None:
    times = np.arange(5, dtype=np.float64) * 0.25
    velocity = np.array([1.0, 2.0, -0.5])
    positions = times[:, None, None] * velocity[None, None, :]
    trajectory = make_trajectory(positions, times=times)
    axes = ("x", "y", "z")[:rank]
    q = np.array([0.0, 0.8, 1.7])
    result = compute_self_intermediate_scattering(
        trajectory,
        q_magnitudes=q,
        isotropic=True,
        axes=axes,
        max_lag=2,
    )
    projected_speed = np.linalg.norm(velocity[:rank])
    arguments = np.outer(result.lag_times * projected_speed, q)
    if rank == 1:
        expected = np.cos(arguments)
    elif rank == 2:
        expected = scipy_j0(arguments)
    else:
        expected = scipy_spherical_jn(0, arguments)
    expected[:, 0] = 1.0
    expected[0, :] = 1.0
    np.testing.assert_allclose(result.values, expected, rtol=3.0e-15, atol=3.0e-15)
    assert result.isotropic
    assert result.values.dtype == np.float64


@pytest.mark.parametrize("rank", [1, 2, 3])
def test_scattering_gaussian_increment_limit(rank: int) -> None:
    rng = np.random.default_rng(7610 + rank)
    sigma = 0.24
    increments = rng.normal(scale=sigma, size=(18000, 1, 3))
    positions = np.concatenate(
        [np.zeros((1, 1, 3)), np.cumsum(increments, axis=0)],
        axis=0,
    )
    trajectory = make_trajectory(positions)
    q = np.array([0.4, 0.9, 1.5])
    result = compute_self_intermediate_scattering(
        trajectory,
        q_magnitudes=q,
        isotropic=True,
        axes=("x", "y", "z")[:rank],
        max_lag=1,
    )
    expected = np.exp(-0.5 * q * q * sigma * sigma)
    np.testing.assert_allclose(result.values[1], expected, rtol=0.012, atol=0.004)


def test_scattering_rotated_subspace_and_out_of_subspace_rejection() -> None:
    direction = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    times = np.arange(6, dtype=np.float64) * 0.1
    velocity = np.array([2.0, -0.5, 1.0])
    positions = times[:, None, None] * velocity[None, None, :]
    trajectory = make_trajectory(positions, times=times)
    q_vectors = np.array([direction, 2.0 * direction])
    result = compute_self_intermediate_scattering(
        trajectory,
        q_vectors=q_vectors,
        isotropic=False,
        projection_basis=direction,
        max_lag=3,
    )
    expected_phase = np.outer(
        result.lag_times,
        q_vectors @ direction * np.dot(velocity, direction),
    )
    np.testing.assert_allclose(result.values, np.exp(1j * expected_phase))
    np.testing.assert_allclose(
        result.projected_q_vectors[:, 0],
        q_vectors @ direction,
    )
    with pytest.raises(ValueError, match="selected analysis subspace"):
        compute_self_intermediate_scattering(
            trajectory,
            q_vectors=[[0.0, 0.0, 1.0]],
            isotropic=False,
            projection_basis=direction,
            max_lag=1,
        )


def test_scattering_matches_fine_van_hove_transform() -> None:
    rng = np.random.default_rng(8821)
    increments = rng.normal(scale=0.35, size=(1200, 3, 3))
    positions = np.concatenate(
        [np.zeros((1, 3, 3)), np.cumsum(increments, axis=0)],
        axis=0,
    )
    trajectory = make_trajectory(positions)
    q = np.array([0.5, 1.0, 1.8])
    scattering = compute_self_intermediate_scattering(
        trajectory,
        q_magnitudes=q,
        isotropic=True,
        max_lag=1,
        origin_stride=2,
    )
    van_hove = compute_self_van_hove(
        trajectory,
        lag_steps=[1],
        origin_stride=2,
        n_bins=1400,
    )
    kernel = scipy_spherical_jn(
        0,
        van_hove.radial_centers[:, None] * q[None, :],
    )
    transformed = np.sum(
        van_hove.shell_probability[0, :, None] * kernel,
        axis=0,
    )
    np.testing.assert_allclose(
        scattering.values[1],
        transformed,
        rtol=2.5e-4,
        atol=2.5e-4,
    )


def test_scattering_block_invariance_atom_order_and_counts() -> None:
    rng = np.random.default_rng(9012)
    positions = np.cumsum(rng.normal(scale=0.2, size=(12, 5, 3)), axis=0)
    trajectory = make_trajectory(positions)
    kwargs = dict(
        atom_indices=[4, 1, 3],
        q_magnitudes=[1.2, 0.0, 1.2, 0.4],
        isotropic=True,
        max_lag=5,
        lag_stride=2,
        origin_stride=2,
    )
    small = compute_self_intermediate_scattering(
        trajectory,
        atom_block_size=1,
        origin_block_size=1,
        **kwargs,
    )
    broad = compute_self_intermediate_scattering(
        trajectory,
        atom_block_size=3,
        origin_block_size=12,
        **kwargs,
    )
    np.testing.assert_array_equal(small.atom_indices, [4, 1, 3])
    np.testing.assert_array_equal(small.q_magnitudes, [1.2, 0.0, 1.2, 0.4])
    np.testing.assert_array_equal(small.n_samples, broad.n_samples)
    np.testing.assert_allclose(small.values, broad.values, rtol=3.0e-15, atol=3.0e-15)
    expected = np.array(
        [3 * ((trajectory.n_frames - 1 - lag) // 2 + 1) for lag in small.lag_steps]
    )
    np.testing.assert_array_equal(small.n_samples, expected)
    np.testing.assert_array_equal(small.values[:, 1], 1.0)
    np.testing.assert_array_equal(small.values[:, 0], small.values[:, 2])


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"q_magnitudes": [1.0], "isotropic": False}, ValueError),
        ({"q_vectors": [[1.0, 0.0, 0.0]], "isotropic": True}, ValueError),
        ({"q_magnitudes": [1.0], "q_vectors": [[1.0, 0.0, 0.0]]}, ValueError),
        ({"q_magnitudes": []}, ValueError),
        ({"q_magnitudes": [-1.0]}, ValueError),
        ({"q_magnitudes": [np.inf]}, ValueError),
        ({"q_magnitudes": [True]}, TypeError),
        ({"q_vectors": [[1.0, 0.0]], "isotropic": False}, ValueError),
        ({"q_vectors": [[np.nan, 0.0, 0.0]], "isotropic": False}, ValueError),
        ({"q_vectors": [[True, False, False]], "isotropic": False}, TypeError),
        ({"q_magnitudes": [1.0], "isotropic": 1}, TypeError),
    ],
)
def test_scattering_rejects_invalid_mode_and_q_inputs(kwargs, error) -> None:
    trajectory = make_trajectory(np.zeros((4, 1, 3), dtype=np.float64))
    with pytest.raises(error):
        compute_self_intermediate_scattering(trajectory, max_lag=1, **kwargs)


def test_scattering_result_is_deeply_immutable_and_constructor_checks_zero_lag() -> None:
    trajectory = make_trajectory(np.zeros((4, 1, 3), dtype=np.float64))
    result = compute_self_intermediate_scattering(
        trajectory,
        q_magnitudes=[0.0, 1.0],
        max_lag=2,
    )
    with pytest.raises(ValueError):
        result.values[0, 0] = 0.0
    with pytest.raises(ValueError):
        result.q_magnitudes[0] = 2.0
    with pytest.raises(TypeError):
        result.metadata["new"] = 1

    invalid_values = np.array(result.values, copy=True)
    invalid_values[0, 1] = 0.5
    with pytest.raises(ValueError, match="lag zero"):
        SelfIntermediateScatteringResult(
            lag_steps=result.lag_steps,
            lag_times=result.lag_times,
            values=invalid_values,
            q_magnitudes=result.q_magnitudes,
            q_vectors=None,
            projected_q_vectors=None,
            n_samples=result.n_samples,
            atom_indices=result.atom_indices,
            projection_basis=result.projection_basis,
            signature=result.signature,
            metadata=result.metadata,
        )


def test_scattering_public_exports() -> None:
    import mdstats
    import mdstats.analysis as analysis

    assert mdstats.compute_self_intermediate_scattering is compute_self_intermediate_scattering
    assert analysis.compute_self_intermediate_scattering is compute_self_intermediate_scattering
    assert "compute_self_intermediate_scattering" in mdstats.__all__
    assert "compute_self_intermediate_scattering" in analysis.__all__
    assert "SelfIntermediateScatteringResult" in mdstats.__all__
    assert "SelfIntermediateScatteringResult" in analysis.__all__


def test_scattering_private_q_chunking_is_numerically_invariant(monkeypatch) -> None:
    import mdstats.analysis.displacement_dynamics as module

    rng = np.random.default_rng(1902)
    positions = np.cumsum(rng.normal(scale=0.15, size=(9, 4, 3)), axis=0)
    trajectory = make_trajectory(positions)
    q = np.linspace(0.0, 3.0, 17)
    reference = compute_self_intermediate_scattering(
        trajectory,
        q_magnitudes=q,
        max_lag=4,
        origin_stride=2,
    )
    monkeypatch.setattr(module, "_SCATTERING_TRANSIENT_TARGET_BYTES", 64)
    chunked = compute_self_intermediate_scattering(
        trajectory,
        q_magnitudes=q,
        max_lag=4,
        origin_stride=2,
    )
    assert chunked.metadata["q_chunk_size"] == 1
    np.testing.assert_array_equal(chunked.q_magnitudes, reference.q_magnitudes)
    np.testing.assert_allclose(chunked.values, reference.values, rtol=0.0, atol=0.0)
