"""Focused D0 tests for displacement preparation and blocked iteration."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    compute_msd,
)
from mdstats.analysis._displacement_common import (
    CollectiveMotionWarning,
    DisplacementInputBundle,
    VariableCellMSDWarning,
    iter_displacement_blocks,
    prepare_displacement_inputs,
    resolve_displacement_block_plan,
)
from mdstats.analysis.msd import _direct_time_averaged_msd


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
        cells = np.repeat((10.0 * np.eye(3))[None, :, :], n_frames, axis=0)
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
            source_files=("d0-test",),
            velocity_source="native",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def legacy_direct(
    positions: np.ndarray,
    lags: np.ndarray,
    *,
    origin_stride: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_lags = lags.size
    n_atoms = positions.shape[1]
    components = np.empty((n_lags, 3), dtype=np.float64)
    tensor = np.empty((n_lags, 3, 3), dtype=np.float64)
    per_atom = np.empty((n_lags, n_atoms), dtype=np.float64)
    n_origins = np.empty(n_lags, dtype=np.int64)
    for index, lag_value in enumerate(lags):
        lag = int(lag_value)
        origins = np.arange(0, positions.shape[0] - lag, origin_stride)
        delta = positions[origins + lag] - positions[origins]
        squared = delta * delta
        n_origins[index] = origins.size
        components[index] = np.mean(squared, axis=(0, 1))
        tensor[index] = np.einsum("oai,oaj->ij", delta, delta) / (
            origins.size * n_atoms
        )
        per_atom[index] = np.mean(np.sum(squared, axis=2), axis=0)
    return np.sum(components, axis=1), components, tensor, per_atom, n_origins


def test_prepare_bundle_resolves_selection_projection_and_immutability() -> None:
    times = np.arange(5, dtype=np.float64) * 0.2
    positions = np.zeros((5, 3, 3), dtype=np.float64)
    positions[:, 0, 0] = times
    positions[:, 1, 1] = 2.0 * times
    positions[:, 2, 2] = -3.0 * times
    collection = make_trajectory(positions)

    bundle = prepare_displacement_inputs(
        collection,
        atom_indices=[2, 0],
        axes=("y", "x"),
    )

    assert isinstance(bundle, DisplacementInputBundle)
    np.testing.assert_array_equal(bundle.atom_indices, [2, 0])
    assert bundle.subspace.labels == ("y", "x")
    assert bundle.signature.projection_labels == ("y", "x")
    np.testing.assert_allclose(bundle.positions[:, 0], positions[:, 2])
    np.testing.assert_allclose(bundle.positions[:, 1], positions[:, 0])
    with pytest.raises(ValueError):
        bundle.positions[0, 0, 0] = 1.0
    with pytest.raises(TypeError):
        bundle.metadata["new"] = 1



def test_rotated_projection_is_applied_to_each_displacement() -> None:
    times = np.arange(4, dtype=np.float64) * 0.25
    direction = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    positions = np.zeros((4, 1, 3), dtype=np.float64)
    positions[:, 0] = times[:, None] * np.array([2.0, -1.0, 3.0])
    collection = make_trajectory(positions, times=times)
    bundle = prepare_displacement_inputs(
        collection,
        projection_basis=direction[None, :],
    )

    block = next(
        iter_displacement_blocks(
            bundle,
            [2],
            atom_block_size=1,
            origin_block_size=2,
        )
    )
    expected_cartesian = positions[2:4, 0] - positions[0:2, 0]
    expected_projected = expected_cartesian @ direction
    np.testing.assert_allclose(block.displacements[:, 0, 0], expected_projected)
    assert bundle.subspace.rank == 1
    assert bundle.subspace.labels is None


def test_iterator_order_values_and_complete_coverage() -> None:
    times = np.arange(5, dtype=np.float64) * 0.2
    positions = np.zeros((5, 3, 3), dtype=np.float64)
    positions[:, 0] = times[:, None] * np.array([1.0, 2.0, 3.0])
    positions[:, 1] = times[:, None] * np.array([-1.0, 0.5, 4.0])
    positions[:, 2] = times[:, None] * np.array([2.0, -3.0, 1.0])
    collection = make_trajectory(positions)
    bundle = prepare_displacement_inputs(
        collection,
        atom_indices=[2, 0],
        axes=("y", "x"),
    )
    lags = np.array([0, 2], dtype=np.int64)
    blocks = list(
        iter_displacement_blocks(
            bundle,
            lags,
            origin_stride=2,
            atom_block_size=1,
            origin_block_size=1,
        )
    )

    observed_order = [
        (block.lag_index, int(block.origin_indices[0]), int(block.atom_indices[0]))
        for block in blocks
    ]
    assert observed_order == [
        (0, 0, 2),
        (0, 0, 0),
        (0, 2, 2),
        (0, 2, 0),
        (0, 4, 2),
        (0, 4, 0),
        (1, 0, 2),
        (1, 0, 0),
        (1, 2, 2),
        (1, 2, 0),
    ]

    samples: dict[tuple[int, int, int], np.ndarray] = {}
    for block in blocks:
        assert block.n_samples == 1
        with pytest.raises(ValueError):
            block.displacements[0, 0, 0] = 99.0
        for oi, origin in enumerate(block.origin_indices):
            for ai, atom in enumerate(block.atom_indices):
                key = (block.lag_step, int(origin), int(atom))
                assert key not in samples
                samples[key] = block.displacements[oi, ai]
                expected_delta = positions[int(origin) + block.lag_step, int(atom)] - positions[
                    int(origin), int(atom)
                ]
                expected = expected_delta[[1, 0]]
                np.testing.assert_allclose(block.displacements[oi, ai], expected)

    assert len(samples) == 10


def test_reference_cell_and_drift_are_resolved_once() -> None:
    n_frames = 5
    cells = np.repeat(np.eye(3)[None, :, :], n_frames, axis=0)
    cells[:, 0, 0] = np.linspace(10.0, 12.0, n_frames)
    fractional = np.zeros((n_frames, 2, 3), dtype=np.float64)
    fractional[:, 0, 0] = 0.2
    fractional[:, 1, 0] = 0.4
    positions = np.einsum("tni,tij->tnj", fractional, cells)
    collection = make_trajectory(
        positions,
        cells=cells,
        atomic_numbers=np.array([3, 11]),
        masses=np.array([1.0, 3.0]),
    )

    with pytest.warns(VariableCellMSDWarning):
        laboratory = prepare_displacement_inputs(collection)
    reference = prepare_displacement_inputs(
        collection,
        coordinate_mode="reference_cell",
        reference_cell="initial",
    )
    assert np.ptp(laboratory.positions[:, 0, 0]) > 0.0
    np.testing.assert_allclose(
        reference.positions,
        np.repeat(reference.positions[0][None, :, :], n_frames, axis=0),
    )

    translated = positions + np.arange(n_frames)[:, None, None] * np.array(
        [0.5, -0.25, 0.0]
    )
    translated_collection = make_trajectory(
        translated,
        cells=cells,
        atomic_numbers=np.array([3, 11]),
        masses=np.array([1.0, 3.0]),
    )
    drift_removed = prepare_displacement_inputs(
        translated_collection,
        coordinate_mode="reference_cell",
        reference_cell="initial",
        drift_mode="center_of_geometry",
    )
    centers = np.mean(drift_removed.positions, axis=1)
    np.testing.assert_allclose(centers, 0.0, atol=1e-14)

    with pytest.warns(CollectiveMotionWarning):
        prepare_displacement_inputs(
            translated_collection,
            atom_indices=[0],
            coordinate_mode="reference_cell",
            reference_cell="initial",
            drift_mode="center_of_geometry",
            drift_atom_indices=[0],
        )


def test_memory_plan_is_deterministic_and_hard_bounded() -> None:
    positions = np.zeros((10, 4, 3), dtype=np.float64)
    collection = make_trajectory(positions)
    bundle = prepare_displacement_inputs(collection)
    lags = np.array([0, 3], dtype=np.int64)

    bytes_per_sample = 120
    plan = resolve_displacement_block_plan(
        bundle,
        lags,
        atom_block_size=2,
        origin_block_size=3,
        memory_target_bytes=6 * bytes_per_sample,
    )
    assert plan.atom_block_size == 2
    assert plan.origin_block_size == 3
    assert plan.estimated_peak_work_bytes == 6 * bytes_per_sample

    reduced = resolve_displacement_block_plan(
        bundle,
        lags,
        memory_target_bytes=2 * bytes_per_sample,
    )
    assert reduced.atom_block_size == 2
    assert reduced.origin_block_size == 1
    assert reduced.estimated_peak_work_bytes <= 2 * bytes_per_sample

    with pytest.raises(ValueError, match="too small"):
        resolve_displacement_block_plan(
            bundle,
            lags,
            memory_target_bytes=bytes_per_sample - 1,
        )


def test_direct_msd_matches_legacy_oracle_for_multiple_blockings() -> None:
    rng = np.random.default_rng(1827)
    increments = rng.normal(size=(12, 5, 3)) * 0.1
    positions = np.cumsum(increments, axis=0)
    collection = make_trajectory(positions)
    bundle = prepare_displacement_inputs(collection, atom_indices=[4, 1, 3, 0])
    lags = np.array([0, 1, 3, 5], dtype=np.int64)
    expected = legacy_direct(bundle.positions, lags, origin_stride=2)

    for atom_block_size, origin_block_size in ((None, None), (1, 1), (2, 3), (4, 2)):
        actual = _direct_time_averaged_msd(
            bundle,
            lags,
            origin_stride=2,
            compute_tensor=True,
            per_atom=True,
            atom_block_size=atom_block_size,
            origin_block_size=origin_block_size,
            memory_target_bytes=None,
        )
        for got, want in zip(actual[:5], expected):
            np.testing.assert_allclose(got, want, rtol=2e-15, atol=2e-17)


def test_compute_msd_direct_records_d0_plan() -> None:
    times = np.arange(8, dtype=np.float64) * 0.1
    positions = np.zeros((8, 3, 3), dtype=np.float64)
    positions[:, 0, 0] = times
    positions[:, 1, 1] = -2.0 * times
    positions[:, 2, 2] = 0.5 * times
    result = compute_msd(
        make_trajectory(positions, times=times),
        backend="direct",
        max_lag=3,
        per_atom=True,
    )
    assert result.metadata["displacement_common_stage"] == "D0"
    assert result.metadata["displacement_atom_block_size"] == 3
    assert result.metadata["displacement_origin_block_size"] == 8
    assert result.metadata["displacement_memory_target_bytes"] is not None
    assert result.signature is not None


def test_lag_and_block_validation_is_strict() -> None:
    positions = np.zeros((5, 2, 3), dtype=np.float64)
    bundle = prepare_displacement_inputs(make_trajectory(positions))

    with pytest.raises(TypeError, match="integers"):
        list(iter_displacement_blocks(bundle, [0.0, 1.0]))
    with pytest.raises(TypeError, match="integers"):
        list(iter_displacement_blocks(bundle, [False, True]))
    with pytest.raises(ValueError, match="strictly increasing"):
        list(iter_displacement_blocks(bundle, [0, 2, 2]))
    with pytest.raises(ValueError, match="largest available"):
        list(iter_displacement_blocks(bundle, [5]))
    with pytest.raises(TypeError, match="origin_stride"):
        list(iter_displacement_blocks(bundle, [0], origin_stride=True))
