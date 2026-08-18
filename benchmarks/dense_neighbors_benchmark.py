#!/usr/bin/env python3
"""Reproducible stage-S0 baseline for the blocked dense neighbor backend."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path

import ase
import networkx
import numpy as np
import scipy

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis._neighbors import (
    NeighborSearchBackend,
    PairCounting,
    build_neighbor_list,
)

DEFAULT_SEED = 20260713


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    geometry: str
    selection: str
    n_atoms: int
    species_counts: dict[str, int]
    cutoff_registry: dict[str, float]
    n_centers: int
    n_candidates: int
    dense_pair_evaluations: int
    accepted_pair_count: int
    block_size: int
    repeat: int
    median_seconds: float
    minimum_seconds: float
    maximum_seconds: float
    peak_tracemalloc_bytes: int


def _collection(
    *,
    n_atoms: int,
    geometry: str,
    seed: int,
) -> AtomisticFrameCollection:
    rng = np.random.default_rng(seed)
    number_density = 0.035
    length = (n_atoms / number_density) ** (1.0 / 3.0)
    if geometry == "orthogonal":
        cell = np.diag([length, length, length])
    elif geometry == "triclinic":
        cell = length * np.array(
            [
                [1.0, 0.0, 0.0],
                [0.24, 1.0, 0.0],
                [0.11, 0.17, 1.0],
            ]
        )
    else:
        raise ValueError(f"Unknown geometry {geometry!r}.")
    fractional = rng.random((1, n_atoms, 3))
    numbers = np.empty(n_atoms, dtype=np.int32)
    numbers[0::2] = 8
    numbers[1::2] = 14
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.array([0], dtype=np.int64),
        atomic_numbers=numbers,
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool),
        steps=None,
        times=None,
        cells=cell[None, :, :],
        origins=np.zeros((1, 3)),
        fractional_positions=fractional,
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="dense-neighbor-benchmark",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _case(
    collection: AtomisticFrameCollection,
    selection: str,
) -> tuple[np.ndarray, np.ndarray, float, PairCounting, dict[str, float]]:
    if selection == "all_unordered":
        indices = np.arange(collection.n_atoms, dtype=np.int64)
        return (
            indices,
            indices.copy(),
            3.0,
            PairCounting.UNORDERED_IDENTICAL,
            {"all-all": 3.0},
        )
    if selection == "oxygen_silicon_directed":
        centers = np.flatnonzero(collection.atomic_numbers == 14).astype(np.int64)
        candidates = np.flatnonzero(collection.atomic_numbers == 8).astype(np.int64)
        return (
            centers,
            candidates,
            2.4,
            PairCounting.DIRECTED,
            {"Si-O": 2.4},
        )
    raise ValueError(f"Unknown selection {selection!r}.")


def run_record(
    *,
    n_atoms: int,
    geometry: str,
    selection: str,
    repeat: int,
    block_size: int,
    seed: int,
) -> BenchmarkRecord:
    collection = _collection(n_atoms=n_atoms, geometry=geometry, seed=seed)
    centers, candidates, cutoff, counting, cutoff_registry = _case(
        collection,
        selection,
    )
    kwargs = dict(
        frame_index=0,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=cutoff,
        pair_counting=counting,
        backend=NeighborSearchBackend.DENSE,
        block_size=block_size,
    )
    warmup = build_neighbor_list(collection, **kwargs)
    accepted_pair_count = warmup.n_pairs
    del warmup

    samples: list[float] = []
    for _ in range(repeat):
        gc.collect()
        start = time.perf_counter()
        result = build_neighbor_list(collection, **kwargs)
        samples.append(time.perf_counter() - start)
        if result.n_pairs != accepted_pair_count:
            raise RuntimeError("Dense benchmark output changed between repetitions.")
        del result

    gc.collect()
    tracemalloc.start()
    result = build_neighbor_list(collection, **kwargs)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if result.n_pairs != accepted_pair_count:
        raise RuntimeError("Dense benchmark memory pass changed scientific output.")

    unique, counts = np.unique(collection.atomic_numbers, return_counts=True)
    symbol = {8: "O", 14: "Si"}
    species_counts = {
        symbol.get(int(number), str(int(number))): int(count)
        for number, count in zip(unique, counts, strict=True)
    }
    return BenchmarkRecord(
        geometry=geometry,
        selection=selection,
        n_atoms=n_atoms,
        species_counts=species_counts,
        cutoff_registry=cutoff_registry,
        n_centers=int(centers.size),
        n_candidates=int(candidates.size),
        dense_pair_evaluations=int(centers.size * candidates.size),
        accepted_pair_count=accepted_pair_count,
        block_size=block_size,
        repeat=repeat,
        median_seconds=float(statistics.median(samples)),
        minimum_seconds=float(min(samples)),
        maximum_seconds=float(max(samples)),
        peak_tracemalloc_bytes=int(peak),
    )


def _cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                name = line.split(":", 1)[1].strip()
                if name and name.lower() != "unknown":
                    return name
    except OSError:
        pass
    return platform.processor() or platform.machine() or "unknown"


def _environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": _cpu_name(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "ase": ase.__version__,
        "networkx": networkx.__version__,
        "backend": NeighborSearchBackend.DENSE.value,
    }


def _markdown(payload: dict[str, object]) -> str:
    environment = payload["environment"]
    records = payload["records"]
    lines = [
        "# Dense Neighbor Baseline Report",
        "",
        "This report is a machine-specific stage-S0 baseline. It is not a portable",
        "performance guarantee. Scientific outputs are checked for deterministic pair",
        "counts before timing and memory results are accepted.",
        "",
        "## Environment",
        "",
    ]
    assert isinstance(environment, dict)
    for key, value in environment.items():
        lines.append(f"- **{key}:** `{value}`")
    lines.extend(
        [
            "",
            "## Measurements",
            "",
            "| Geometry | Selection | N | Species | Cutoff registry (A) | Centers | Candidates | Dense evaluations | Accepted | Median (s) | Min (s) | Max (s) | Peak tracemalloc (MiB) |",
            "|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    assert isinstance(records, list)
    for raw in records:
        assert isinstance(raw, dict)
        peak_mib = int(raw["peak_tracemalloc_bytes"]) / (1024.0 * 1024.0)
        species = ", ".join(
            f"{key}:{value}" for key, value in raw["species_counts"].items()
        )
        cutoffs = ", ".join(
            f"{key}:{value:g}" for key, value in raw["cutoff_registry"].items()
        )
        lines.append(
            "| {geometry} | {selection} | {n_atoms} | {species} | {cutoffs} | "
            "{n_centers} | {n_candidates} | {dense_pair_evaluations} | "
            "{accepted_pair_count} | {median_seconds:.6f} | {minimum_seconds:.6f} | "
            "{maximum_seconds:.6f} | {peak:.3f} |".format(
                peak=peak_mib,
                species=species,
                cutoffs=cutoffs,
                **raw,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The dense backend performs `n_centers * n_candidates` minimum-image pair",
            "evaluations before cutoff filtering. `UNORDERED_IDENTICAL` removes duplicate",
            "output pairs but does not reduce the current dense displacement calculation.",
            "These records establish the correctness/performance reference for stage S1.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[64, 128, 256])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--block-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("benchmarks/dense_neighbors_benchmark.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("benchmarks/dense_neighbors_benchmark.md"),
    )
    args = parser.parse_args()
    records: list[BenchmarkRecord] = []
    for geometry_index, geometry in enumerate(("orthogonal", "triclinic")):
        for selection_index, selection in enumerate(
            ("all_unordered", "oxygen_silicon_directed")
        ):
            for size_index, size in enumerate(args.sizes):
                records.append(
                    run_record(
                        n_atoms=size,
                        geometry=geometry,
                        selection=selection,
                        repeat=args.repeat,
                        block_size=args.block_size,
                        seed=(
                            args.seed
                            + geometry_index * 100_000
                            + selection_index * 10_000
                            + size_index
                        ),
                    )
                )
    payload: dict[str, object] = {
        "schema": "mdstats.dense-neighbor-baseline.v1",
        "seed": args.seed,
        "environment": _environment(),
        "records": [asdict(record) for record in records],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(_markdown(payload))
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_md}")


if __name__ == "__main__":
    main()
