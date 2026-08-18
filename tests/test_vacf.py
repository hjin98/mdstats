"""Deterministic tests for the velocity autocorrelation module."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_vacf,
)
from mdstats.analysis import (
    CollectiveMotionVACFWarning,
    FiniteDifferenceVelocityWarning,
)
from mdstats.exceptions import MissingVelocityError, TrajectoryRequiredError


def make_collection(
    velocities: np.ndarray | None,
    *,
    times: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    masses: np.ndarray | None = None,
    frame_semantics: FrameSemantics = FrameSemantics.TRAJECTORY,
    velocity_source: str = "native",
) -> AtomisticFrameCollection:
    """Construct a valid synthetic collection with zero positions."""
    if velocities is None:
        if times is None:
            n_frames = 4
        else:
            n_frames = int(np.asarray(times).size)
        n_atoms = 2 if atomic_numbers is None else int(np.asarray(atomic_numbers).size)
    else:
        velocities = np.asarray(velocities, dtype=np.float64)
        n_frames, n_atoms, _ = velocities.shape

    if times is None and frame_semantics is FrameSemantics.TRAJECTORY:
        times = np.arange(n_frames, dtype=np.float64) * 0.1
    elif times is not None:
        times = np.asarray(times, dtype=np.float64)
    if atomic_numbers is None:
        atomic_numbers = np.ones(n_atoms, dtype=np.int32)
    if masses is None:
        masses = np.ones(n_atoms, dtype=np.float64)

    cells = np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0)
    provenance_velocity = (
        "discarded_for_ensemble"
        if frame_semantics is FrameSemantics.ENSEMBLE
        else velocity_source
    )
    return AtomisticFrameCollection(
        frame_semantics=frame_semantics,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.asarray(masses, dtype=np.float64),
        pbc=np.array([True, True, True]),
        steps=(
            np.arange(n_frames, dtype=np.int64)
            if frame_semantics is FrameSemantics.TRAJECTORY
            else None
        ),
        times=times,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        velocities=(None if frame_semantics is FrameSemantics.ENSEMBLE else velocities),
        provenance=FrameCollectionProvenance(
            source_format="lammps-custom-dump",
            source_files=("synthetic",),
            velocity_source=provenance_velocity,
            coordinate_normalization=(
                "independent_frame_wrapping"
                if frame_semantics is FrameSemantics.ENSEMBLE
                else "native_unwrapped_fractional"
            ),
            stress_source=None,
            units_source="synthetic",
        ),
    )


def manual_tensor(
    velocities: np.ndarray,
    weights: np.ndarray,
    lag: int,
    origin_stride: int = 1,
) -> np.ndarray:
    origins = np.arange(0, velocities.shape[0] - lag, origin_stride)
    return (
        np.einsum(
            "ona,onb,n->ab",
            velocities[origins],
            velocities[origins + lag],
            weights,
            optimize=True,
        )
        / origins.size
    )


def test_constant_velocity_raw_sum_and_means() -> None:
    velocity = np.array([2.0, -1.0, 0.5])
    velocities = np.repeat(velocity[None, None, :], 8, axis=0)
    velocities = np.repeat(velocities, 3, axis=1)
    collection = make_collection(velocities)

    result = compute_vacf(collection, max_lag=5, backend="direct", per_atom=True)

    expected_components = 3.0 * velocity**2
    np.testing.assert_allclose(
        result.components_sum,
        np.repeat(expected_components[None, :], 6, axis=0),
    )
    np.testing.assert_allclose(result.scalar_mean, np.dot(velocity, velocity))
    np.testing.assert_allclose(result.normalized_scalar(), 1.0)
    np.testing.assert_allclose(
        np.sum(result.per_atom_scalar, axis=1), result.scalar_sum, atol=1e-13
    )
    np.testing.assert_array_equal(result.n_origins, [8, 7, 6, 5, 4, 3])


def test_direct_and_fft_agree_for_full_nonsymmetric_tensor() -> None:
    rng = np.random.default_rng(42)
    velocities = rng.normal(size=(65, 7, 3))
    collection = make_collection(velocities)
    explicit_weights = np.linspace(0.25, 1.75, 7)

    direct = compute_vacf(
        collection,
        max_lag=31,
        weights=explicit_weights,
        backend="direct",
        per_atom_indices=[0, 3, 6],
    )
    fft = compute_vacf(
        collection,
        max_lag=31,
        weights=explicit_weights,
        backend="fft",
        atom_block_size=2,
        per_atom_indices=[0, 3, 6],
    )

    np.testing.assert_allclose(fft.tensor_sum, direct.tensor_sum, atol=2.0e-13)
    np.testing.assert_allclose(fft.components_sum, direct.components_sum, atol=2e-13)
    np.testing.assert_allclose(fft.scalar_sum, direct.scalar_sum, atol=3e-13)
    np.testing.assert_allclose(
        fft.per_atom_components, direct.per_atom_components, atol=2e-13
    )
    # Generic finite data need not give a symmetric positive-lag tensor.
    assert not np.allclose(direct.tensor_sum[1], direct.tensor_sum[1].T)


def test_fft_agrees_for_odd_even_lengths_and_block_sizes() -> None:
    rng = np.random.default_rng(11)
    for n_frames in (32, 33):
        velocities = rng.normal(size=(n_frames, 5, 3))
        collection = make_collection(velocities)
        reference = compute_vacf(collection, max_lag=12, backend="direct")
        for block_size in (1, 2, 5, 99):
            result = compute_vacf(
                collection,
                max_lag=12,
                backend="fft",
                atom_block_size=block_size,
            )
            np.testing.assert_allclose(
                result.tensor_sum, reference.tensor_sum, atol=2e-13
            )


def test_tensor_orientation_matches_direct_definition() -> None:
    velocities = np.zeros((5, 1, 3), dtype=np.float64)
    velocities[:, 0, 0] = [1.0, 2.0, 4.0, 8.0, 16.0]
    velocities[:, 0, 1] = [3.0, 1.0, -1.0, 2.0, 5.0]
    collection = make_collection(velocities)

    result = compute_vacf(collection, max_lag=2, backend="fft")
    for lag in range(3):
        expected = manual_tensor(velocities, np.ones(1), lag)
        np.testing.assert_allclose(result.tensor_sum[lag], expected, atol=1e-13)
    assert result.tensor_sum[1, 0, 1] != pytest.approx(result.tensor_sum[1, 1, 0])


def test_no_cross_atom_terms_are_introduced() -> None:
    velocities = np.zeros((6, 2, 3), dtype=np.float64)
    velocities[:, 0, 0] = [1, 2, 3, 4, 5, 6]
    velocities[:, 1, 0] = [6, -5, 4, -3, 2, -1]
    collection = make_collection(velocities)

    result = compute_vacf(collection, max_lag=5, backend="fft", per_atom=True)
    expected = []
    for lag in range(6):
        self_terms = sum(
            np.mean(velocities[: 6 - lag, atom, 0] * velocities[lag:, atom, 0])
            for atom in range(2)
        )
        expected.append(self_terms)
    np.testing.assert_allclose(result.scalar_sum, expected, atol=1e-13)
    np.testing.assert_allclose(
        np.sum(result.per_atom_scalar, axis=1), result.scalar_sum, atol=1e-13
    )


def test_uniform_mass_and_explicit_weighting() -> None:
    velocities = np.ones((5, 2, 3), dtype=np.float64)
    masses = np.array([2.0, 5.0])
    collection = make_collection(velocities, masses=masses)

    uniform = compute_vacf(collection, max_lag=1, weights="uniform")
    mass = compute_vacf(collection, max_lag=1, weights="mass")
    explicit = compute_vacf(collection, max_lag=1, weights=[0.5, 3.0])

    np.testing.assert_allclose(uniform.scalar_sum, 6.0)
    np.testing.assert_allclose(mass.scalar_sum, 21.0)
    np.testing.assert_allclose(explicit.scalar_sum, 10.5)
    assert mass.metadata["correlation_units"] == "amu*Å^2/ps^2"
    np.testing.assert_allclose(mass.scalar_mean, 3.0)


def test_species_selection_and_per_atom_subset() -> None:
    velocities = np.zeros((5, 4, 3), dtype=np.float64)
    velocities[:, :, 0] = np.arange(1, 5)[None, :]
    collection = make_collection(
        velocities,
        atomic_numbers=np.array([11, 8, 11, 19]),
        masses=np.array([23.0, 16.0, 23.0, 39.0]),
    )

    result = compute_vacf(
        collection,
        species=["Na", "K"],
        max_lag=2,
        per_atom_indices=[3, 0],
    )

    np.testing.assert_array_equal(result.atom_indices, [0, 2, 3])
    np.testing.assert_array_equal(result.per_atom_indices, [3, 0])
    np.testing.assert_allclose(result.per_atom_scalar[:, 0], 4.0**2)
    np.testing.assert_allclose(result.per_atom_scalar[:, 1], 1.0**2)


def test_drift_removal_eliminates_uniform_translation() -> None:
    velocities = np.zeros((8, 3, 3), dtype=np.float64)
    velocities[:] = np.array([2.0, -1.0, 0.25])
    collection = make_collection(velocities, masses=np.array([1.0, 2.0, 3.0]))

    uncorrected = compute_vacf(collection, max_lag=3)
    corrected = compute_vacf(
        collection,
        max_lag=3,
        drift_mode="center_of_mass",
    )

    assert uncorrected.scalar_sum[0] > 0.0
    np.testing.assert_allclose(corrected.scalar_sum, 0.0, atol=1e-28)


def test_subset_drift_warning() -> None:
    velocities = np.ones((6, 3, 3), dtype=np.float64)
    collection = make_collection(velocities)

    with pytest.warns(CollectiveMotionVACFWarning):
        result = compute_vacf(
            collection,
            atom_indices=[0, 1],
            drift_mode="center_of_geometry",
            drift_atom_indices=[0, 1],
        )
    np.testing.assert_allclose(result.scalar_sum, 0.0)


def test_direction_projection_and_component_normalization() -> None:
    velocities = np.zeros((6, 1, 3), dtype=np.float64)
    velocities[:, 0, 0] = 2.0
    velocities[:, 0, 1] = 1.0
    velocities[:, 0, 2] = 0.5
    collection = make_collection(velocities)

    result = compute_vacf(collection, max_lag=2)

    np.testing.assert_allclose(result.project_direction([2, 0, 0]), 4.0)
    np.testing.assert_allclose(result.project_direction([1, 1, 0], mean=True), 4.5)
    np.testing.assert_allclose(result.normalized_components(), 1.0)


def test_normalization_rejects_zero_amplitude() -> None:
    velocities = np.zeros((5, 1, 3), dtype=np.float64)
    collection = make_collection(velocities)
    result = compute_vacf(collection, max_lag=2)

    with pytest.raises(ValueError, match="lag-zero amplitude"):
        result.normalized_scalar()
    with pytest.raises(ValueError, match="lag-zero amplitude"):
        result.normalized_components()


def test_compute_tensor_false_retains_components() -> None:
    rng = np.random.default_rng(8)
    collection = make_collection(rng.normal(size=(20, 3, 3)))
    result = compute_vacf(collection, compute_tensor=False, max_lag=6, backend="fft")

    assert result.tensor_sum is None
    np.testing.assert_allclose(result.scalar_sum, np.sum(result.components_sum, axis=1))
    with pytest.raises(ValueError, match="requires tensor_sum"):
        result.project_direction([1, 0, 0])


def test_direct_origin_stride_counts_and_fft_restriction() -> None:
    collection = make_collection(np.ones((8, 2, 3), dtype=np.float64))
    result = compute_vacf(
        collection,
        max_lag=5,
        origin_stride=2,
        backend="direct",
    )
    np.testing.assert_array_equal(result.n_origins, [4, 4, 3, 3, 2, 2])

    with pytest.raises(ValueError, match="origin_stride == 1"):
        compute_vacf(collection, origin_stride=2, backend="fft")


def test_ensemble_missing_velocity_and_nonuniform_time_guards() -> None:
    ensemble = make_collection(None, frame_semantics=FrameSemantics.ENSEMBLE)
    with pytest.raises(TrajectoryRequiredError):
        compute_vacf(ensemble)

    collection = make_collection(np.ones((4, 1, 3), dtype=np.float64))
    collection.velocities = None
    with pytest.raises(MissingVelocityError):
        compute_vacf(collection)

    nonuniform = make_collection(
        np.ones((4, 1, 3), dtype=np.float64),
        times=np.array([0.0, 0.1, 0.25, 0.4]),
    )
    with pytest.raises(ValueError, match="uniformly sampled"):
        compute_vacf(nonuniform)


def test_invalid_weights_lags_and_per_atom_indices() -> None:
    collection = make_collection(np.ones((5, 2, 3), dtype=np.float64))

    with pytest.raises(ValueError, match=r"expected \(2,\)"):
        compute_vacf(collection, weights=[1.0])
    with pytest.raises(ValueError, match="nonnegative"):
        compute_vacf(collection, weights=[1.0, -1.0])
    with pytest.raises(ValueError, match="all be zero"):
        compute_vacf(collection, weights=[0.0, 0.0])
    with pytest.raises(ValueError, match="exceeds"):
        compute_vacf(collection, max_lag=5)
    with pytest.raises(ValueError, match="subset"):
        compute_vacf(collection, atom_indices=[0], per_atom_indices=[1])
    with pytest.raises(ValueError, match="positive integer"):
        compute_vacf(collection, atom_block_size=0)


def test_finite_difference_velocity_warning_and_metadata() -> None:
    collection = make_collection(
        np.ones((6, 1, 3), dtype=np.float64),
        velocity_source="finite_difference",
    )
    with pytest.warns(FiniteDifferenceVelocityWarning):
        result = compute_vacf(collection, max_lag=2)
    assert result.metadata["velocity_source"] == "finite_difference"


def test_harmonic_signal_has_expected_direct_correlation() -> None:
    n_frames = 64
    phase = 2.0 * np.pi * np.arange(n_frames) / 16.0
    velocities = np.zeros((n_frames, 1, 3), dtype=np.float64)
    velocities[:, 0, 0] = np.cos(phase)
    collection = make_collection(velocities)

    result = compute_vacf(collection, max_lag=20, backend="fft")
    expected = [
        np.mean(np.cos(phase[: n_frames - lag]) * np.cos(phase[lag:]))
        for lag in range(21)
    ]
    np.testing.assert_allclose(result.scalar_sum, expected, atol=1e-13)


def test_constant_vacf_reproduces_ballistic_msd_relation() -> None:
    dt = 0.05
    velocity = np.array([1.0, 2.0, -0.5])
    velocities = np.repeat(velocity[None, None, :], 40, axis=0)
    collection = make_collection(
        velocities,
        times=np.arange(40, dtype=np.float64) * dt,
    )
    result = compute_vacf(collection, max_lag=20)

    # For constant C, MSD(t) = 2 * integral_0^t (t-tau) C d tau = C t^2.
    expected_msd = np.dot(velocity, velocity) * result.lag_times**2
    derived_msd = result.scalar_mean * result.lag_times**2
    np.testing.assert_allclose(derived_msd, expected_msd)


def test_auto_backend_selects_fft_for_long_problem() -> None:
    rng = np.random.default_rng(91)
    collection = make_collection(rng.normal(size=(512, 4, 3)))
    result = compute_vacf(collection, max_lag=256, backend="auto")

    assert result.backend == "fft"
    assert result.metadata["fft_length"] is not None
    assert result.metadata["source_format"] == "lammps-custom-dump"
