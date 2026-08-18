#!/usr/bin/env python3
"""Reproducible S2 fixed-cell Verlet-cache benchmark and equivalence audit."""

from __future__ import annotations

import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mdstats import (  # noqa: E402
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
)
from mdstats.analysis._neighbor_compare import (  # noqa: E402
    assert_neighbor_results_equal,
)
from mdstats.analysis._neighbors import (  # noqa: E402
    NeighborSearchBackend,
    PairCounting,
    build_neighbor_list,
)
from mdstats.analysis._verlet_cache import (  # noqa: E402
    NeighborSearchSession,
    VerletCacheOptions,
)


def make_collection(
    *,
    n_atoms: int,
    n_frames: int,
    step_scale: float,
    seed: int,
) -> AtomisticFrameCollection:
    rng = np.random.default_rng(seed)
    density = 0.018
    length = float((n_atoms / density) ** (1.0 / 3.0))
    cell = np.array(
        [
            [length, 0.0, 0.0],
            [0.14 * length, 0.96 * length, 0.0],
            [0.08 * length, 0.11 * length, 0.93 * length],
        ]
    )
    base = rng.random((n_atoms, 3))
    increments = rng.normal(scale=step_scale / length, size=(n_frames, n_atoms, 3))
    increments[0] = 0.0
    fractional = base[None, :, :] + np.cumsum(increments, axis=0)
    cells = np.repeat(cell[None, :, :], n_frames, axis=0)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.ones(n_atoms, dtype=np.int32),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("verlet-benchmark",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def evaluate_fresh(collection: AtomisticFrameCollection, cutoff: float) -> list:
    indices = np.arange(collection.n_atoms, dtype=np.int64)
    return [
        build_neighbor_list(
            collection,
            frame_index=frame,
            center_indices=indices,
            candidate_neighbor_indices=indices,
            cutoff=cutoff,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
            backend=NeighborSearchBackend.CELL_LIST,
        )
        for frame in range(collection.n_frames)
    ]


def evaluate_cached(
    collection: AtomisticFrameCollection,
    cutoff: float,
    skin: float,
) -> tuple[list, dict]:
    indices = np.arange(collection.n_atoms, dtype=np.int64)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=skin))
    results = [
        session.build_neighbor_list(
            frame_index=frame,
            center_indices=indices,
            candidate_neighbor_indices=indices,
            cutoff=cutoff,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
        for frame in range(collection.n_frames)
    ]
    return results, session.statistics().to_dict()


def timed(callable_, repetitions: int = 1) -> tuple[float, float, float]:
    values = []
    for _ in range(repetitions):
        start = time.perf_counter()
        callable_()
        values.append(time.perf_counter() - start)
    return min(values), statistics.median(values), max(values)


def main() -> None:
    cutoff = 2.5
    skin = 0.6
    records = []
    for motion_name, step_scale in (("solid", 0.006), ("diffusive", 0.045)):
        for n_atoms in (64, 128, 256):
            collection = make_collection(
                n_atoms=n_atoms,
                n_frames=12,
                step_scale=step_scale,
                seed=13000 + n_atoms + int(step_scale * 1000),
            )
            fresh = evaluate_fresh(collection, cutoff)
            cached, stats = evaluate_cached(collection, cutoff, skin)
            for actual, expected in zip(cached, fresh, strict=True):
                assert_neighbor_results_equal(actual, expected)

            fresh_min, fresh_median, fresh_max = timed(
                lambda: evaluate_fresh(collection, cutoff)
            )
            cache_min, cache_median, cache_max = timed(
                lambda: evaluate_cached(collection, cutoff, skin)
            )
            records.append(
                {
                    "motion": motion_name,
                    "n_atoms": n_atoms,
                    "n_frames": collection.n_frames,
                    "cutoff_angstrom": cutoff,
                    "skin_angstrom": skin,
                    "fresh_cell_list_seconds": {
                        "minimum": fresh_min,
                        "median": fresh_median,
                        "maximum": fresh_max,
                    },
                    "verlet_seconds": {
                        "minimum": cache_min,
                        "median": cache_median,
                        "maximum": cache_max,
                    },
                    "speedup_median": fresh_median / cache_median,
                    "cache_statistics": stats,
                    "equivalence": "passed",
                }
            )

    payload = {
        "schema": "mdstats.verlet-benchmark.v1",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "records": records,
    }
    output = ROOT / "benchmarks" / "verlet_cache_benchmark.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    for record in records:
        stats = record["cache_statistics"]
        print(
            record["motion"],
            record["n_atoms"],
            f"speedup={record['speedup_median']:.3f}x",
            f"rebuilds={stats['rebuilds']}",
            f"reuse={stats['reuse_evaluations']}",
        )


if __name__ == "__main__":
    main()
