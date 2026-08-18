"""Regression tests for interpreter-free numerical hot paths."""

from __future__ import annotations

import ast
import inspect
from types import SimpleNamespace

import numpy as np

from mdstats.plotting.density_block_direct import _reverse_source_target_csr
from mdstats.plotting.density_block_routing import (
    bitset_popcount,
    bitset_popcounts,
    pack_local_indices,
    unpack_local_bitset,
)
from mdstats.plotting.density_tiled_mesh import _precise_vertices_and_keys
from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    prepare_plotting_coordinate_view,
)


def _scalar_pack(indices: np.ndarray, count: int) -> np.ndarray:
    words = np.zeros((count + 63) // 64, dtype=np.uint64)
    for index in np.unique(indices):
        words[int(index) // 64] |= np.uint64(1) << np.uint64(int(index) % 64)
    return words


def _scalar_unpack(words: np.ndarray, count: int) -> np.ndarray:
    result: list[int] = []
    for word_index, raw in enumerate(words):
        value = int(raw)
        while value:
            least = value & -value
            bit = least.bit_length() - 1
            index = 64 * word_index + bit
            if index < count:
                result.append(index)
            value ^= least
    return np.asarray(result, dtype=np.int64)


def test_vectorized_bitset_kernels_match_scalar_reference() -> None:
    rng = np.random.default_rng(41)
    block = (16, 16, 16)
    count = int(np.prod(block))
    indices = rng.integers(0, count, size=3500, dtype=np.int64)
    expected_words = _scalar_pack(indices, count)
    actual_words = pack_local_indices(indices, block)
    np.testing.assert_array_equal(actual_words, expected_words)
    np.testing.assert_array_equal(
        unpack_local_bitset(actual_words, block),
        _scalar_unpack(expected_words, count),
    )
    rows = rng.integers(
        0,
        np.iinfo(np.uint64).max,
        size=(257, actual_words.size),
        dtype=np.uint64,
    )
    expected_counts = np.asarray(
        [sum(int(value).bit_count() for value in row) for row in rows],
        dtype=np.int64,
    )
    np.testing.assert_array_equal(bitset_popcounts(rows), expected_counts)
    assert bitset_popcount(rows[0]) == int(expected_counts[0])


def test_reverse_csr_vectorization_matches_scalar_reference() -> None:
    source_rows = (
        np.asarray((0, 2, 4), dtype=np.int32),
        np.asarray((1, 2), dtype=np.int32),
        np.asarray((0, 3, 4), dtype=np.int32),
        np.asarray((2, 4), dtype=np.int32),
    )
    source_ranges = np.concatenate(
        (
            np.asarray([0], dtype=np.int64),
            np.cumsum([row.size for row in source_rows], dtype=np.int64),
        )
    )
    targets = np.concatenate(source_rows)
    atlas = SimpleNamespace(
        source_to_target_block_indices=targets,
        source_to_target_block_ranges=source_ranges,
        source_block_count=len(source_rows),
        target_block_count=5,
        source_target_edge_count=int(targets.size),
    )
    ranges, sources = _reverse_source_target_csr(atlas)
    expected = [[] for _ in range(5)]
    for source, row in enumerate(source_rows):
        for target in row:
            expected[int(target)].append(source)
    for target, values in enumerate(expected):
        start, stop = int(ranges[target]), int(ranges[target + 1])
        assert sources[start:stop].tolist() == values


def _scalar_precise(
    raw_vertices: np.ndarray,
    volume: np.ndarray,
    cell_start: np.ndarray,
    logical_shape: np.ndarray,
    level32: np.float32,
):
    local = np.asarray(raw_vertices, dtype=np.float64)
    precise_lifted = np.empty_like(local)
    keys = []
    for row, vertex in enumerate(local):
        nearest = np.rint(vertex).astype(np.int64)
        residual = np.abs(vertex - nearest)
        axis = int(np.argmax(residual))
        if float(residual[axis]) <= 1.0e-10:
            lifted_node = cell_start + nearest
            precise_lifted[row] = lifted_node
            keys.append((3, *map(int, lifted_node)))
            continue
        endpoint0 = nearest.copy()
        endpoint0[axis] = int(np.floor(vertex[axis] + 1.0e-7))
        endpoint1 = endpoint0.copy()
        endpoint1[axis] += 1
        value0 = float(volume[tuple(endpoint0)])
        value1 = float(volume[tuple(endpoint1)])
        denominator = value1 - value0
        factor = (
            float(vertex[axis] - endpoint0[axis])
            if denominator == 0.0
            else (float(level32) - value0) / denominator
        )
        factor = min(1.0, max(0.0, factor))
        precise = endpoint0.astype(np.float64)
        precise[axis] += factor
        lifted_base = cell_start + endpoint0
        precise_lifted[row] = cell_start + precise
        keys.append((axis, *map(int, lifted_base)))
    fractional = precise_lifted / logical_shape[None, :]
    fractional[np.abs(fractional) < 2.0e-14] = 0.0
    fractional[np.abs(fractional - 1.0) < 2.0e-14] = 1.0
    return fractional, tuple(keys)


def test_vectorized_precise_vertices_match_scalar_reference() -> None:
    rng = np.random.default_rng(9)
    volume = rng.random((17, 18, 19), dtype=np.float32)
    count = 5000
    base = np.column_stack(
        (
            rng.integers(0, 16, size=count),
            rng.integers(0, 17, size=count),
            rng.integers(0, 18, size=count),
        )
    ).astype(np.int64)
    axes = rng.integers(0, 3, size=count, dtype=np.int64)
    vertices = base.astype(np.float64)
    vertices[np.arange(count), axes] += rng.random(count)
    cell_start = np.asarray((3, 5, 7), dtype=np.int64)
    logical_shape = np.asarray((64, 65, 66), dtype=np.float64)
    level = np.float32(0.43)
    expected_fractional, expected_keys = _scalar_precise(
        vertices, volume, cell_start, logical_shape, level
    )
    actual_fractional, actual_keys = _precise_vertices_and_keys(
        vertices,
        volume,
        cell_start=cell_start,
        logical_shape=logical_shape,
        level32=level,
    )
    np.testing.assert_array_equal(actual_fractional, expected_fractional)
    np.testing.assert_array_equal(
        actual_keys, np.asarray(expected_keys, dtype=np.int64)
    )


def test_batched_laboratory_transform_matches_frame_loop() -> None:
    rng = np.random.default_rng(12)
    n_frames = 11
    n_atoms = 37
    fractional = rng.random((n_frames, n_atoms, 3))
    cells = np.repeat(np.eye(3)[None, :, :], n_frames, axis=0)
    cells[:, 0, 0] = np.linspace(1.0, 1.08, n_frames)
    cells[:, 1, 1] = np.linspace(1.0, 0.96, n_frames)
    collection = AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.ones(n_atoms, dtype=np.int32),
        masses=np.ones(n_atoms, dtype=np.float64),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64),
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3), dtype=np.float64),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-hotpath",
            source_files=("synthetic-hotpath",),
            velocity_source="synthetic",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )
    display_cell = np.eye(3)
    frames = tuple(range(n_frames))
    view = prepare_plotting_coordinate_view(
        collection,
        frame_indices=frames,
        display_cell=display_cell,
        spatial_mode="laboratory",
        framework_atom_indices=(0,),
        framework_fractional_by_frame=fractional[:, [0], :],
    )
    expected = np.empty_like(fractional)
    for frame in frames:
        expected[frame] = fractional[frame] @ cells[frame]
    np.testing.assert_allclose(view.positions, expected, rtol=0.0, atol=2.0e-15)
    np.testing.assert_array_equal(
        view.translation_corrections, np.zeros((n_frames, 3))
    )


def test_registered_dense_kernels_contain_no_python_for_or_while_loops() -> None:
    functions = (
        pack_local_indices,
        unpack_local_bitset,
        bitset_popcounts,
        _reverse_source_target_csr,
        _precise_vertices_and_keys,
    )
    for function in functions:
        tree = ast.parse(inspect.getsource(function))
        loops = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.For, ast.While))
        ]
        assert not loops, f"{function.__qualname__} reintroduced Python loops"
