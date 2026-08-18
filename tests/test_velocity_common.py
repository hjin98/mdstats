"""Focused tests for shared velocity-input preparation."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis._velocity_common import (
    compute_drift_velocity,
    prepare_velocity_inputs,
    resolve_per_atom_output,
    resolve_velocity_weights,
    validate_uniform_time_grid,
)
from mdstats.exceptions import MissingVelocityError, TrajectoryRequiredError


def make_collection(
    velocities: np.ndarray | None,
    *,
    times: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    masses: np.ndarray | None = None,
    frame_semantics: FrameSemantics = FrameSemantics.TRAJECTORY,
) -> AtomisticFrameCollection:
    if velocities is None:
        n_frames = 4 if times is None else int(np.asarray(times).size)
        n_atoms = 2 if atomic_numbers is None else int(np.asarray(atomic_numbers).size)
    else:
        velocities = np.asarray(velocities, dtype=np.float64)
        n_frames, n_atoms, _ = velocities.shape
    if times is None and frame_semantics is FrameSemantics.TRAJECTORY:
        times = np.arange(n_frames, dtype=np.float64) * 0.2
    if atomic_numbers is None:
        atomic_numbers = np.ones(n_atoms, dtype=np.int32)
    if masses is None:
        masses = np.ones(n_atoms, dtype=np.float64)
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
        times=None if times is None else np.asarray(times, dtype=np.float64),
        cells=np.repeat(np.eye(3)[None, :, :] * 10.0, n_frames, axis=0),
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        velocities=(None if frame_semantics is FrameSemantics.ENSEMBLE else velocities),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source=(
                "discarded_for_ensemble"
                if frame_semantics is FrameSemantics.ENSEMBLE
                else ("missing" if velocities is None else "native")
            ),
            coordinate_normalization=(
                "independent_frame_wrapping"
                if frame_semantics is FrameSemantics.ENSEMBLE
                else "native_unwrapped_fractional"
            ),
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_prepare_velocity_inputs_resolves_selection_weights_and_per_atom_order() -> None:
    velocities = np.zeros((6, 4, 3), dtype=np.float64)
    collection = make_collection(
        velocities,
        atomic_numbers=np.array([11, 8, 11, 19]),
        masses=np.array([23.0, 16.0, 23.0, 39.0]),
    )

    result = prepare_velocity_inputs(
        collection,
        analysis_name="test spectrum",
        species=["Na", "K"],
        weights="mass",
        per_atom_indices=[3, 0],
    )

    assert result.sample_spacing_ps == pytest.approx(0.2)
    assert result.velocities is collection.velocities
    np.testing.assert_array_equal(result.atom_indices, [0, 2, 3])
    np.testing.assert_allclose(result.atom_weights, [23.0, 23.0, 39.0])
    assert result.weight_sum == pytest.approx(85.0)
    assert result.weighting == "mass"
    assert result.weight_units == "amu"
    assert result.correlation_units == "amu*Å^2/ps^2"
    np.testing.assert_array_equal(result.per_atom_indices, [3, 0])
    np.testing.assert_array_equal(result.per_atom_local_indices, [2, 0])


def test_prepare_velocity_inputs_computes_center_of_mass_drift() -> None:
    velocities = np.zeros((3, 3, 3), dtype=np.float64)
    velocities[:, 0, 0] = 1.0
    velocities[:, 1, 0] = 4.0
    velocities[:, 2, 0] = 100.0
    collection = make_collection(velocities, masses=np.array([1.0, 3.0, 2.0]))

    result = prepare_velocity_inputs(
        collection,
        analysis_name="VACF",
        atom_indices=[0, 1],
        drift_mode="center_of_mass",
        drift_atom_indices=[0, 1],
    )

    np.testing.assert_allclose(result.drift_velocity[:, 0], 3.25)
    np.testing.assert_allclose(result.drift_velocity[:, 1:], 0.0)
    assert result.drift_matches_measured_subset is True
    np.testing.assert_array_equal(result.drift_atom_indices, [0, 1])


def test_center_of_geometry_and_center_of_mass_are_distinct() -> None:
    velocities = np.zeros((2, 2, 3), dtype=np.float64)
    velocities[:, 0, 0] = 0.0
    velocities[:, 1, 0] = 4.0
    collection = make_collection(velocities, masses=np.array([1.0, 3.0]))
    indices = np.array([0, 1], dtype=np.int64)

    geometry = compute_drift_velocity(
        collection, velocities, indices, drift_mode="center_of_geometry"
    )
    mass = compute_drift_velocity(
        collection, velocities, indices, drift_mode="center_of_mass"
    )
    np.testing.assert_allclose(geometry[:, 0], 2.0)
    np.testing.assert_allclose(mass[:, 0], 3.0)


def test_weight_resolution_copies_explicit_input_and_rejects_invalid_values() -> None:
    collection = make_collection(np.zeros((3, 2, 3), dtype=np.float64))
    selected = np.array([0, 1], dtype=np.int64)
    raw = np.array([0.5, 2.0], dtype=np.float64)
    values, kind, units, correlation_units = resolve_velocity_weights(
        collection, selected, raw
    )
    raw[0] = 99.0
    np.testing.assert_allclose(values, [0.5, 2.0])
    assert kind == "explicit"
    assert units == "dimensionless"
    assert correlation_units == "Å^2/ps^2"

    with pytest.raises(ValueError, match="shape"):
        resolve_velocity_weights(collection, selected, [1.0])
    with pytest.raises(ValueError, match="nonnegative"):
        resolve_velocity_weights(collection, selected, [1.0, -1.0])
    with pytest.raises(ValueError, match="all be zero"):
        resolve_velocity_weights(collection, selected, [0.0, 0.0])


def test_per_atom_output_preserves_request_order_and_validates_subset() -> None:
    selected = np.array([0, 2, 4], dtype=np.int64)
    canonical, local = resolve_per_atom_output(selected, False, [4, 0], 5)
    np.testing.assert_array_equal(canonical, [4, 0])
    np.testing.assert_array_equal(local, [2, 0])

    with pytest.raises(ValueError, match="subset"):
        resolve_per_atom_output(selected, False, [1], 5)
    with pytest.raises(ValueError, match="duplicate"):
        resolve_per_atom_output(selected, False, [0, 0], 5)


def test_uniform_time_and_velocity_contract_errors() -> None:
    irregular = make_collection(
        np.zeros((4, 2, 3), dtype=np.float64),
        times=np.array([0.0, 0.1, 0.25, 0.4]),
    )
    with pytest.raises(ValueError, match="uniformly sampled"):
        validate_uniform_time_grid(irregular, analysis_name="Welch spectrum")

    ensemble = make_collection(
        np.zeros((4, 2, 3), dtype=np.float64),
        frame_semantics=FrameSemantics.ENSEMBLE,
        times=None,
    )
    with pytest.raises(TrajectoryRequiredError):
        prepare_velocity_inputs(ensemble, analysis_name="Welch spectrum")

    missing = make_collection(np.zeros((4, 2, 3), dtype=np.float64))
    missing.velocities = None
    with pytest.raises(MissingVelocityError):
        prepare_velocity_inputs(missing, analysis_name="Welch spectrum")


def test_prepare_velocity_inputs_rejects_inconsistent_drift_arguments() -> None:
    collection = make_collection(np.zeros((4, 2, 3), dtype=np.float64))
    with pytest.raises(ValueError, match="drift selection"):
        prepare_velocity_inputs(
            collection,
            analysis_name="VACF",
            drift_atom_indices=[0],
        )
    with pytest.raises(ValueError, match="drift_mode"):
        prepare_velocity_inputs(
            collection,
            analysis_name="VACF",
            drift_mode="invalid",  # type: ignore[arg-type]
        )
