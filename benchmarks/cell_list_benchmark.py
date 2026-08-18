#!/usr/bin/env python3
"""Reproducible S1 dense-equivalence and cell-list benchmark."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import ase
import networkx
import numpy as np
import scipy

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis._cell_list import (
    build_cell_list_neighbor_list_with_diagnostics,
)
from mdstats.analysis._neighbor_compare import assert_neighbor_results_equal
from mdstats.analysis._neighbors import (
    NeighborSearchBackend,
    PairCounting,
    build_neighbor_list,
    compute_safe_cutoff,
)

DEFAULT_SEED = 20260713


@dataclass(frozen=True, slots=True)
class CellListBenchmarkRecord:
    geometry: str
    selection: str
    n_atoms: int
    n_centers: int
    n_candidates: int
    cutoff: float
    dense_pair_evaluations: int
    cell_exact_pair_evaluations: int
    candidate_fraction: float
    accepted_pair_count: int
    bin_counts: tuple[int, int, int]
    stencil_size: int
    occupied_candidate_bins: int
    reduction_applied: bool
    repeat: int
    dense_median_seconds: float
    cell_list_median_seconds: float
    speedup_dense_over_cell_list: float


def _collection(*, n_atoms: int, geometry: str, seed: int) -> AtomisticFrameCollection:
    rng = np.random.default_rng(seed)
    number_density = 0.035
    length = (n_atoms / number_density) ** (1.0 / 3.0)
    if geometry == "orthogonal":
        cell = np.diag([length, length, length])
    elif geometry == "triclinic":
        cell = length * np.array(
            [
                [1.0, 0.0, 0.0],
                [0.32, 1.0, 0.0],
                [0.16, 0.21, 1.0],
            ]
        )
    elif geometry == "highly_skewed":
        cell = length * np.array(
            [
                [1.0, 0.0, 0.0],
                [0.82, 0.36, 0.0],
                [0.18, 0.09, 0.92],
            ]
        )
    else:
        raise ValueError(f"Unknown geometry {geometry!r}.")
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
        fractional_positions=rng.random((1, n_atoms, 3)),
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="cell-list-benchmark",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def _case(
    collection: AtomisticFrameCollection, selection: str
) -> tuple[np.ndarray, np.ndarray, float, PairCounting]:
    safe = compute_safe_cutoff(collection, frame_indices=[0])
    if selection == "all_unordered":
        indices = np.arange(collection.n_atoms, dtype=np.int64)
        cutoff = min(3.0, 0.90 * safe)
        return indices, indices.copy(), cutoff, PairCounting.UNORDERED_IDENTICAL
    if selection == "oxygen_silicon_directed":
        centers = np.flatnonzero(collection.atomic_numbers == 14).astype(np.int64)
        candidates = np.flatnonzero(collection.atomic_numbers == 8).astype(np.int64)
        cutoff = min(2.4, 0.90 * safe)
        return centers, candidates, cutoff, PairCounting.DIRECTED
    raise ValueError(f"Unknown selection {selection!r}.")


def _median_runtime(function, *, repeat: int) -> float:
    samples: list[float] = []
    for _ in range(repeat):
        gc.collect()
        start = time.perf_counter()
        function()
        samples.append(time.perf_counter() - start)
    return float(statistics.median(samples))


def run_record(
    *, n_atoms: int, geometry: str, selection: str, repeat: int, seed: int
) -> CellListBenchmarkRecord:
    collection = _collection(n_atoms=n_atoms, geometry=geometry, seed=seed)
    centers, candidates, cutoff, counting = _case(collection, selection)
    dense_kwargs = dict(
        frame_index=0,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=cutoff,
        pair_counting=counting,
        backend=NeighborSearchBackend.DENSE,
    )
    dense = build_neighbor_list(collection, **dense_kwargs)
    cell_list, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
        collection,
        frame_index=0,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=cutoff,
        pair_counting=counting,
    )
    assert_neighbor_results_equal(cell_list, dense)

    dense_seconds = _median_runtime(
        lambda: build_neighbor_list(collection, **dense_kwargs), repeat=repeat
    )
    cell_seconds = _median_runtime(
        lambda: build_cell_list_neighbor_list_with_diagnostics(
            collection,
            frame_index=0,
            center_indices=centers,
            candidate_neighbor_indices=candidates,
            cutoff=cutoff,
            pair_counting=counting,
        ),
        repeat=repeat,
    )
    dense_evaluations = int(centers.size * candidates.size)
    candidate_fraction = (
        diagnostics.exact_pair_evaluations / dense_evaluations
        if dense_evaluations
        else 0.0
    )
    return CellListBenchmarkRecord(
        geometry=geometry,
        selection=selection,
        n_atoms=n_atoms,
        n_centers=int(centers.size),
        n_candidates=int(candidates.size),
        cutoff=cutoff,
        dense_pair_evaluations=dense_evaluations,
        cell_exact_pair_evaluations=diagnostics.exact_pair_evaluations,
        candidate_fraction=float(candidate_fraction),
        accepted_pair_count=dense.n_pairs,
        bin_counts=diagnostics.bin_counts,
        stencil_size=diagnostics.stencil_size,
        occupied_candidate_bins=diagnostics.occupied_candidate_bins,
        reduction_applied=diagnostics.reduction_applied,
        repeat=repeat,
        dense_median_seconds=dense_seconds,
        cell_list_median_seconds=cell_seconds,
        speedup_dense_over_cell_list=(
            dense_seconds / cell_seconds if cell_seconds > 0.0 else float("inf")
        ),
    )


def _cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
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
        "dense_backend": NeighborSearchBackend.DENSE.value,
        "cell_list_backend": NeighborSearchBackend.CELL_LIST.value,
    }


def _markdown(payload: dict[str, object]) -> str:
    environment = payload["environment"]
    records = payload["records"]
    assert isinstance(environment, dict)
    assert isinstance(records, list)
    lines = [
        "# Stage S1 Cell-List Equivalence and Benchmark Report",
        "",
        "Every timed cell-list record was first compared with the dense oracle for",
        "exact atom-pair and image-shift equality and tolerance-bounded vector and",
        "distance equality. Timings are machine-specific and are not portable",
        "performance guarantees.",
        "",
        "## Environment",
        "",
    ]
    for key, value in environment.items():
        lines.append(f"- **{key}:** `{value}`")
    lines.extend(
        [
            "",
            "## Measurements",
            "",
            "| Geometry | Selection | N | Dense evals | Cell evals | Candidate fraction | Accepted | Bins | Stencil | Reduced | Dense median (s) | Cell median (s) | Speedup |",
            "|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|",
        ]
    )
    for raw in records:
        assert isinstance(raw, dict)
        bins = "x".join(str(value) for value in raw["bin_counts"])
        lines.append(
            "| {geometry} | {selection} | {n_atoms} | {dense_pair_evaluations} | "
            "{cell_exact_pair_evaluations} | {candidate_fraction:.4f} | "
            "{accepted_pair_count} | {bins} | {stencil_size} | "
            "{reduction_applied} | {dense_median_seconds:.6f} | "
            "{cell_list_median_seconds:.6f} | {speedup_dense_over_cell_list:.2f}x |".format(
                bins=bins, **raw
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The dense backend evaluates the full center-candidate product. The",
            "cell-list backend evaluates only atom pairs found through the exact",
            "metric-aware bin stencil, then applies the same original-cell MIC and",
            "strict physical cutoff. Candidate fraction measures geometric pruning,",
            "not the accepted-neighbor fraction. S1 remains single-frame and does not",
            "reuse candidates across trajectory frames.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[64, 128, 256])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("benchmarks/cell_list_benchmark.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("benchmarks/cell_list_benchmark.md"),
    )
    args = parser.parse_args()
    records: list[CellListBenchmarkRecord] = []
    for geometry_index, geometry in enumerate(
        ("orthogonal", "triclinic", "highly_skewed")
    ):
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
                        seed=(
                            args.seed
                            + geometry_index * 100_000
                            + selection_index * 10_000
                            + size_index
                        ),
                    )
                )
    payload: dict[str, object] = {
        "schema": "mdstats.cell-list-benchmark.v1",
        "seed": args.seed,
        "environment": _environment(),
        "records": [asdict(record) for record in records],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n")
    args.output_md.write_text(_markdown(payload))
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_md}")


if __name__ == "__main__":
    main()
