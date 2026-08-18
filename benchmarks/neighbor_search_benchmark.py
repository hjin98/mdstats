"""Reproducible S4 benchmark for the production periodic-neighbor subsystem.

The benchmark serves two purposes:

1. measure the conservative dense/cell-list crossover used by ``backend='auto'``;
2. exercise representative crystal, molten-salt, interface, skewed-cell, and
   trajectory workloads through the public coordination API.

It is not a universal hardware tuning result.  The recorded threshold is a
portable conservative default, while users may override it explicitly.
"""

from __future__ import annotations

# The benchmark is directly executable from its own directory.
# ruff: noqa: E402

import argparse
import json
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from ase import Atoms
from ase.io import read

from mdstats import (
    AtomisticFrameCollection,
    FrameCollectionProvenance,
    FrameSemantics,
    NeighborSearchOptions,
    NeighborSearchSession,
    compute_coordination_distribution,
)
from mdstats.analysis._neighbors import (
    NeighborSearchBackend,
    PairCounting,
    build_neighbor_list,
)
from mdstats.analysis._cell_list import build_cell_list_neighbor_list_with_diagnostics
from mdstats.analysis._neighbor_compare import assert_neighbor_results_equal

DEFAULT_THRESHOLD = 32_768
DEFAULT_SKIN = 0.5


@dataclass(frozen=True)
class TimedValue:
    seconds: float


def _time_call(
    function: Callable[[], Any], *, repeats: int = 3
) -> tuple[Any, TimedValue]:
    """Return the last value and median wall time after one warm-up."""
    if repeats < 1:
        raise ValueError("repeats must be positive")
    function()  # deterministic warm-up outside measurements
    elapsed: list[float] = []
    value: Any = None
    for _ in range(repeats):
        start = time.perf_counter()
        value = function()
        elapsed.append(time.perf_counter() - start)
    return value, TimedValue(seconds=float(statistics.median(elapsed)))


def _provenance(label: str, *, trajectory: bool) -> FrameCollectionProvenance:
    return FrameCollectionProvenance(
        source_format="ase-structure-collection" if trajectory else "ase-structure",
        source_files=(label,),
        velocity_source="native" if trajectory else "unavailable",
        coordinate_normalization=(
            "native_unwrapped_fractional"
            if trajectory
            else "independent_frame_wrapping"
        ),
        stress_source=None,
        units_source="angstrom",
    )


def _collection_from_atoms(
    atoms: Atoms,
    *,
    label: str,
    n_frames: int = 1,
    variable_cell: bool = False,
    displacement_scale: float = 0.0,
    seed: int = 0,
) -> AtomisticFrameCollection:
    rng = np.random.default_rng(seed)
    base_cell = np.asarray(atoms.cell.array, dtype=float)
    base_fractional = np.asarray(atoms.get_scaled_positions(wrap=True), dtype=float)
    cells: list[np.ndarray] = []
    fractional: list[np.ndarray] = []
    drift = np.zeros_like(base_fractional)
    for frame in range(n_frames):
        if variable_cell:
            strain = np.array(
                [
                    [1.0 + 3.0e-4 * frame, 0.0, 0.0],
                    [1.5e-4 * frame, 1.0 - 1.5e-4 * frame, 0.0],
                    [0.0, 1.0e-4 * frame, 1.0 + 2.0e-4 * frame],
                ]
            )
            cell = base_cell @ strain
        else:
            cell = base_cell.copy()
        if frame:
            drift += rng.normal(scale=displacement_scale, size=drift.shape)
        cells.append(cell)
        fractional.append(base_fractional + drift)
    return AtomisticFrameCollection(
        frame_semantics=(
            FrameSemantics.TRAJECTORY if n_frames > 1 else FrameSemantics.ENSEMBLE
        ),
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray(atoms.numbers, dtype=np.int32),
        masses=np.asarray(atoms.get_masses(), dtype=float),
        pbc=np.asarray(atoms.pbc, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64) if n_frames > 1 else None,
        times=np.arange(n_frames, dtype=float) if n_frames > 1 else None,
        cells=np.asarray(cells),
        origins=np.zeros((n_frames, 3), dtype=float),
        fractional_positions=np.asarray(fractional),
        velocities=(
            np.zeros((n_frames, len(atoms), 3), dtype=float) if n_frames > 1 else None
        ),
        provenance=_provenance(label, trajectory=n_frames > 1),
    )


def _random_binary_atoms(
    n_each: int,
    *,
    cell: np.ndarray,
    symbols: tuple[str, str] = ("Na", "Cl"),
    seed: int,
) -> Atoms:
    rng = np.random.default_rng(seed)
    symbols_all = [symbols[0]] * n_each + [symbols[1]] * n_each
    scaled = rng.random((2 * n_each, 3))
    return Atoms(symbols_all, scaled_positions=scaled, cell=cell, pbc=True)


def _mixed_interface_atoms(
    lta: Atoms, *, n_salt_each: int = 192, seed: int = 9
) -> Atoms:
    """Build a deterministic geometry with framework and salt-rich slabs."""
    rng = np.random.default_rng(seed)
    base_cell = np.asarray(lta.cell.array, dtype=float)
    cell = base_cell.copy()
    cell[2] *= 2.0
    framework_scaled = np.asarray(lta.get_scaled_positions(wrap=True), dtype=float)
    framework_scaled[:, 2] *= 0.48
    salt_scaled = rng.random((2 * n_salt_each, 3))
    salt_scaled[:, 2] = 0.52 + 0.46 * salt_scaled[:, 2]
    symbols = (
        list(lta.get_chemical_symbols()) + ["Na"] * n_salt_each + ["Cl"] * n_salt_each
    )
    scaled = np.vstack((framework_scaled, salt_scaled))
    return Atoms(symbols, scaled_positions=scaled, cell=cell, pbc=True)


def _hydrogen_collection(
    n_atoms: int, *, skewed: bool = False, seed: int = 0
) -> AtomisticFrameCollection:
    rng = np.random.default_rng(seed + n_atoms)
    length = float((n_atoms / 0.025) ** (1.0 / 3.0))
    if skewed:
        cell = np.array(
            [
                [length, 0.0, 0.0],
                [0.45 * length, 0.90 * length, 0.0],
                [0.30 * length, 0.25 * length, 0.84 * length],
            ]
        )
    else:
        cell = np.diag([length, length, length])
    atoms = Atoms(
        ["H"] * n_atoms,
        scaled_positions=rng.random((n_atoms, 3)),
        cell=cell,
        pbc=True,
    )
    return _collection_from_atoms(atoms, label=f"random-H-{n_atoms}-skew-{skewed}")


def _kernel_crossover(sizes: list[int], repeats: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for n_atoms in sizes:
        collection = _hydrogen_collection(n_atoms, seed=7126)
        indices = np.arange(n_atoms, dtype=np.int64)
        kwargs = dict(
            collection=collection,
            frame_index=0,
            center_indices=indices,
            candidate_neighbor_indices=indices,
            cutoff=2.5,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
        dense, dense_timing = _time_call(
            lambda: build_neighbor_list(**kwargs, backend=NeighborSearchBackend.DENSE),
            repeats=repeats,
        )
        (cell_result, cell_diag), cell_timing = _time_call(
            lambda: build_cell_list_neighbor_list_with_diagnostics(**kwargs),
            repeats=repeats,
        )
        assert_neighbor_results_equal(dense, cell_result)
        work = n_atoms * (n_atoms - 1) // 2
        records.append(
            {
                "n_atoms": n_atoms,
                "estimated_dense_pair_work": work,
                "dense_seconds": dense_timing.seconds,
                "cell_list_seconds": cell_timing.seconds,
                "cell_list_speedup": dense_timing.seconds / cell_timing.seconds,
                "dense_estimated_peak_temporary_bytes": int(
                    min(n_atoms, 256) * n_atoms * 4 * 8
                ),
                "cell_list_estimated_peak_temporary_bytes": int(
                    max(cell_diag.exact_pair_evaluations, 1) * 6 * 8
                ),
                "cell_list_exact_pair_evaluations": cell_diag.exact_pair_evaluations,
                "accepted_pairs": cell_result.n_pairs,
                "candidate_efficiency": (
                    0.0
                    if cell_diag.exact_pair_evaluations == 0
                    else cell_result.n_pairs / cell_diag.exact_pair_evaluations
                ),
                "auto_backend_at_default_threshold": (
                    "dense" if work < DEFAULT_THRESHOLD else "cell_list"
                ),
            }
        )
    return records


def _coordination_benchmark(
    *,
    name: str,
    collection: AtomisticFrameCollection,
    species_a: str,
    species_b: str,
    cutoff: float,
    repeats: int,
) -> dict[str, Any]:
    modes = {
        "dense": NeighborSearchOptions(backend="dense"),
        "cell_list": NeighborSearchOptions(backend="cell_list", cache_mode="none"),
        "auto": NeighborSearchOptions(
            backend="auto", cache_mode="none", dense_pair_threshold=DEFAULT_THRESHOLD
        ),
    }
    results: dict[str, Any] = {}
    timings: dict[str, TimedValue] = {}
    for label, options in modes.items():
        result, timing = _time_call(
            lambda options=options: compute_coordination_distribution(
                collection,
                species_a,
                species_b,
                cutoff=cutoff,
                neighbor_search_options=options,
            ),
            repeats=repeats,
        )
        results[label] = result
        timings[label] = timing
    np.testing.assert_array_equal(
        results["dense"].per_atom_per_frame,
        results["cell_list"].per_atom_per_frame,
    )
    np.testing.assert_array_equal(
        results["dense"].per_atom_per_frame,
        results["auto"].per_atom_per_frame,
    )
    auto_diag = results["auto"].metadata["neighbor_search"]
    cell_diag = results["cell_list"].metadata["neighbor_search"]
    return {
        "name": name,
        "n_atoms": collection.n_atoms,
        "n_frames": collection.n_frames,
        "species_a": species_a,
        "species_b": species_b,
        "cutoff_angstrom": cutoff,
        "dense_seconds": timings["dense"].seconds,
        "cell_list_seconds": timings["cell_list"].seconds,
        "auto_seconds": timings["auto"].seconds,
        "cell_list_speedup": timings["dense"].seconds / timings["cell_list"].seconds,
        "auto_speedup": timings["dense"].seconds / timings["auto"].seconds,
        "dense_estimated_peak_temporary_bytes": int(
            min(len(results["dense"].per_atom_per_frame[0]), 256)
            * max(
                auto_diag["requests"][0]["estimated_dense_pair_work"]
                // max(len(results["dense"].per_atom_per_frame[0]), 1),
                1,
            )
            * 4
            * 8
        ),
        "cell_list_estimated_peak_temporary_bytes": int(
            max(cell_diag["candidate_pair_evaluations"], 1) * 6 * 8
        ),
        "auto_backend_selected": auto_diag["backend_selected"],
        "auto_policy_backend": auto_diag["backend_policy"],
        "estimated_dense_pair_work": auto_diag["requests"][0][
            "estimated_dense_pair_work"
        ],
        "candidate_pair_evaluations": cell_diag["candidate_pair_evaluations"],
        "accepted_pairs": cell_diag["accepted_pairs"],
        "candidate_efficiency": cell_diag["candidate_efficiency"],
        "exact_outputs_equal": True,
    }


def _trajectory_benchmark(
    *,
    name: str,
    collection: AtomisticFrameCollection,
    species_a: str,
    species_b: str,
    cutoff: float,
    repeats: int,
) -> dict[str, Any]:
    fresh_options = NeighborSearchOptions(backend="cell_list", cache_mode="none")
    cache_options = NeighborSearchOptions(
        backend="cell_list",
        cache_mode="verlet",
        skin=DEFAULT_SKIN,
        deformation_aware=True,
    )
    fresh, fresh_timing = _time_call(
        lambda: compute_coordination_distribution(
            collection,
            species_a,
            species_b,
            cutoff=cutoff,
            neighbor_search_options=fresh_options,
        ),
        repeats=repeats,
    )
    cached, cached_timing = _time_call(
        lambda: compute_coordination_distribution(
            collection,
            species_a,
            species_b,
            cutoff=cutoff,
            neighbor_search_options=cache_options,
        ),
        repeats=repeats,
    )
    np.testing.assert_array_equal(fresh.per_atom_per_frame, cached.per_atom_per_frame)

    numbers = np.asarray(collection.atomic_numbers)
    za = int(Atoms(species_a).numbers[0])
    zb = int(Atoms(species_b).numbers[0])
    centers = np.flatnonzero(numbers == za).astype(np.int64)
    candidates = np.flatnonzero(numbers == zb).astype(np.int64)
    session = NeighborSearchSession(collection, cache_options.to_verlet_options())
    rebuild_times: list[float] = []
    reuse_times: list[float] = []
    for frame in range(collection.n_frames):
        before = session.statistics()
        start = time.perf_counter()
        session.build_neighbor_list(
            frame_index=frame,
            center_indices=centers,
            candidate_neighbor_indices=candidates,
            cutoff=cutoff,
            pair_counting=PairCounting.DIRECTED,
        )
        elapsed = time.perf_counter() - start
        after = session.statistics()
        if after.rebuilds > before.rebuilds:
            rebuild_times.append(elapsed)
        else:
            reuse_times.append(elapsed)
    stats = session.statistics().to_dict()
    return {
        "name": name,
        "n_atoms": collection.n_atoms,
        "n_frames": collection.n_frames,
        "fresh_cell_list_seconds": fresh_timing.seconds,
        "cached_seconds": cached_timing.seconds,
        "cached_speedup": fresh_timing.seconds / cached_timing.seconds,
        "fresh_seconds_per_frame": fresh_timing.seconds / collection.n_frames,
        "cached_seconds_per_frame": cached_timing.seconds / collection.n_frames,
        "median_rebuild_seconds": (
            None if not rebuild_times else float(statistics.median(rebuild_times))
        ),
        "median_reuse_seconds": (
            None if not reuse_times else float(statistics.median(reuse_times))
        ),
        "fresh_estimated_peak_temporary_bytes": int(
            max(fresh.metadata["neighbor_search"]["candidate_pair_evaluations"], 1)
            * 6
            * 8
        ),
        "cached_estimated_peak_temporary_bytes": int(
            max(stats["current_candidate_pairs"], 1) * 6 * 8
        ),
        "cache_statistics": stats,
        "candidate_accepted_ratio": stats["acceptance_ratio"],
        "exact_outputs_equal": True,
    }


def _markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# S4 periodic-neighbor benchmark report",
        "",
        "This report was generated by `benchmarks/neighbor_search_benchmark.py`.",
        "Times are machine-specific medians after one warm-up. Scientific outputs",
        "were checked exactly against the dense or fresh-cell-list reference.",
        "",
        "## Environment",
        "",
        f"- Python: `{payload['environment']['python']}`",
        f"- NumPy: `{payload['environment']['numpy']}`",
        f"- Platform: `{payload['environment']['platform']}`",
        f"- Repeats: `{payload['configuration']['repeats']}`",
        f"- Default dense-pair threshold: `{payload['configuration']['dense_pair_threshold']}`",
        "",
        "## Kernel crossover",
        "",
        "| Atoms | Dense pair work | Dense (s) | Cell list (s) | Speedup | Auto |",
        "|---:|---:|---:|---:|---:|:---|",
    ]
    for row in payload["kernel_crossover"]:
        lines.append(
            f"| {row['n_atoms']} | {row['estimated_dense_pair_work']} | "
            f"{row['dense_seconds']:.6f} | {row['cell_list_seconds']:.6f} | "
            f"{row['cell_list_speedup']:.2f}x | {row['auto_backend_at_default_threshold']} |"
        )
    lines += [
        "",
        "The conservative threshold keeps very small pair products on the dense",
        "oracle and selects the cell list once the measured scaling advantage is",
        "clear. The threshold is deterministic and user-overridable.",
        "",
        "## Representative single-frame workloads",
        "",
        "| Workload | Atoms | Pair work | Dense (s) | Cell list (s) | Speedup | Auto |",
        "|:---|---:|---:|---:|---:|---:|:---|",
    ]
    for row in payload["representative_workloads"]:
        lines.append(
            f"| {row['name']} | {row['n_atoms']} | {row['estimated_dense_pair_work']} | "
            f"{row['dense_seconds']:.6f} | {row['cell_list_seconds']:.6f} | "
            f"{row['cell_list_speedup']:.2f}x | {row['auto_backend_selected']} |"
        )
    lines += [
        "",
        "## Trajectory cache workloads",
        "",
        "| Workload | Frames | Fresh cell list (s) | Cached (s) | Speedup | Rebuilds | Reuse frames |",
        "|:---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["trajectory_workloads"]:
        stats = row["cache_statistics"]
        lines.append(
            f"| {row['name']} | {row['n_frames']} | "
            f"{row['fresh_cell_list_seconds']:.6f} | {row['cached_seconds']:.6f} | "
            f"{row['cached_speedup']:.2f}x | {stats['rebuilds']} | "
            f"{stats['reuse_evaluations']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Every benchmark comparison passed exact scientific equivalence checks.",
        "- `auto` selected only supported exact backends.",
        "- The cell list shows the intended favorable scaling as pair work grows.",
        "- The cache reports rebuild and reuse timing separately and retains auditable",
        "  rebuild intervals, reasons, safety margins, and singular-value bounds.",
        "- Temporary-memory values are conservative array-size estimates rather than",
        "  process RSS; they are intended for relative backend comparison.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("neighbor_search_benchmark.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "benchmarks/neighbor_search_benchmark.md",
    )
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    lta = read(root / "tests" / "data" / "Na_LTA_relaxed.POSCAR")
    lta_replicated = lta.repeat((2, 2, 1))
    molten = _random_binary_atoms(
        192,
        cell=np.diag([25.5, 25.5, 25.5]),
        seed=1701,
    )
    interface = _mixed_interface_atoms(lta, n_salt_each=192)
    skewed_binary = _random_binary_atoms(
        192,
        cell=np.array([[27.0, 0.0, 0.0], [12.0, 24.0, 0.0], [8.0, 6.0, 22.0]]),
        seed=882,
    )

    representative = [
        _coordination_benchmark(
            name="small Na-LTA framework",
            collection=_collection_from_atoms(lta, label="Na-LTA-168"),
            species_a="Si",
            species_b="O",
            cutoff=2.1,
            repeats=args.repeats,
        ),
        _coordination_benchmark(
            name="replicated Na-LTA 2x2x1",
            collection=_collection_from_atoms(lta_replicated, label="Na-LTA-672"),
            species_a="Si",
            species_b="O",
            cutoff=2.1,
            repeats=args.repeats,
        ),
        _coordination_benchmark(
            name="dense NaCl-like melt",
            collection=_collection_from_atoms(molten, label="NaCl-melt-512"),
            species_a="Na",
            species_b="Cl",
            cutoff=4.0,
            repeats=args.repeats,
        ),
        _coordination_benchmark(
            name="mixed Na-LTA/salt interface",
            collection=_collection_from_atoms(interface, label="LTA-salt-interface"),
            species_a="Na",
            species_b="Cl",
            cutoff=4.0,
            repeats=args.repeats,
        ),
        _coordination_benchmark(
            name="highly skewed binary cell",
            collection=_collection_from_atoms(skewed_binary, label="skewed-binary"),
            species_a="Na",
            species_b="Cl",
            cutoff=4.0,
            repeats=args.repeats,
        ),
    ]

    fixed = _collection_from_atoms(
        molten,
        label="fixed-cell-trajectory",
        n_frames=8,
        variable_cell=False,
        displacement_scale=2.0e-4,
        seed=812,
    )
    variable = _collection_from_atoms(
        molten,
        label="variable-cell-trajectory",
        n_frames=8,
        variable_cell=True,
        displacement_scale=2.0e-4,
        seed=813,
    )
    trajectory = [
        _trajectory_benchmark(
            name="fixed-cell dense-salt trajectory",
            collection=fixed,
            species_a="Na",
            species_b="Cl",
            cutoff=4.0,
            repeats=args.repeats,
        ),
        _trajectory_benchmark(
            name="variable-cell dense-salt trajectory",
            collection=variable,
            species_a="Na",
            species_b="Cl",
            cutoff=4.0,
            repeats=args.repeats,
        ),
    ]

    payload = {
        "schema": "mdstats.neighbor-search-s4-benchmark.v1",
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "configuration": {
            "repeats": args.repeats,
            "dense_pair_threshold": DEFAULT_THRESHOLD,
            "skin_angstrom": DEFAULT_SKIN,
            "kernel_sizes": [64, 128, 256, 512],
        },
        "kernel_crossover": _kernel_crossover([64, 128, 256, 512], args.repeats),
        "representative_workloads": representative,
        "trajectory_workloads": trajectory,
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    args.report.write_text(_markdown_report(payload))
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
