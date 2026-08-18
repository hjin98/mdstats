"""Benchmark LD5 sparse evaluation and canonical-support caching.

Run from the repository root:

    python benchmarks/density_sparse_optimization_benchmark.py
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from statistics import median
from time import perf_counter

import numpy as np

from mdstats.plotting import DensitySourceProvenance, PeriodicWeightedSamples3D
from mdstats.plotting.density_sparse_optimization import (
    clear_density_optimization_caches,
    density_optimization_cache_info,
    get_periodic_gaussian_stencil_support,
    prepare_sparse_canonical_density_optimized,
)
from mdstats.plotting.density_sparse_reference import (
    prepare_sparse_canonical_density_reference,
)

ROOT = Path(__file__).resolve().parent
JSON_PATH = ROOT / "density_sparse_optimization_benchmark.json"
MD_PATH = ROOT / "density_sparse_optimization_benchmark.md"


def _batch(positions: np.ndarray) -> PeriodicWeightedSamples3D:
    weights = np.full(positions.shape[0], 1.0 / positions.shape[0])
    return PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy"
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )


def _timed(callable_, *, repeats: int = 9) -> list[float]:
    values: list[float] = []
    for _ in range(repeats):
        clear_density_optimization_caches()
        gc.collect()
        start = perf_counter()
        callable_()
        values.append(perf_counter() - start)
    return values


def _field_case(name: str, positions: np.ndarray) -> dict[str, object]:
    batch = _batch(positions)
    kwargs = dict(
        grid_shape=(64, 64, 64),
        display_cell=np.eye(3) * 16.0,
        gaussian_bandwidth=0.25,
        field_key=name,
        label=name,
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        max_kernel_pairs=50_000_000,
        max_workspace_bytes=1_500_000_000,
    )
    reference_times = _timed(
        lambda: prepare_sparse_canonical_density_reference(batch, **kwargs)
    )
    optimized_times = _timed(
        lambda: prepare_sparse_canonical_density_optimized(
            batch,
            pair_chunk_size=262_144,
            cache_stencil_supports=False,
            **kwargs,
        )
    )
    reference = prepare_sparse_canonical_density_reference(batch, **kwargs)
    optimized = prepare_sparse_canonical_density_optimized(
        batch,
        pair_chunk_size=262_144,
        cache_stencil_supports=False,
        **kwargs,
    )
    reference_median = median(reference_times)
    optimized_median = median(optimized_times)
    return {
        "name": name,
        "sample_count": int(positions.shape[0]),
        "active_node_count": int(reference.active_flat_indices.size),
        "kernel_pair_count": int(reference.metadata["kernel_pair_count"]),
        "reference_seconds": reference_times,
        "optimized_seconds": optimized_times,
        "reference_median_seconds": reference_median,
        "optimized_median_seconds": optimized_median,
        "speedup": reference_median / optimized_median,
        "active_indices_equal": bool(
            np.array_equal(
                reference.active_flat_indices, optimized.active_flat_indices
            )
        ),
        "relative_l1_error": float(
            np.sum(np.abs(reference.active_values - optimized.active_values))
            / np.sum(np.abs(reference.active_values))
        ),
        "relative_linf_error": float(
            np.max(np.abs(reference.active_values - optimized.active_values))
            / np.max(np.abs(reference.active_values))
        ),
    }


def _cache_case() -> dict[str, object]:
    kwargs = dict(
        grid_shape=(96, 96, 96),
        display_cell=np.eye(3) * 16.0,
        gaussian_bandwidth=0.35,
        kernel_tail_tolerance=1.0e-8,
        max_workspace_bytes=2_000_000_000,
    )
    cold: list[float] = []
    warm: list[float] = []
    for _ in range(11):
        clear_density_optimization_caches()
        gc.collect()
        start = perf_counter()
        get_periodic_gaussian_stencil_support(**kwargs)
        cold.append(perf_counter() - start)
        start = perf_counter()
        get_periodic_gaussian_stencil_support(**kwargs)
        warm.append(perf_counter() - start)
    cold_median = median(cold)
    warm_median = median(warm)
    info = density_optimization_cache_info()
    return {
        "cold_seconds": cold,
        "warm_seconds": warm,
        "cold_median_seconds": cold_median,
        "warm_median_seconds": warm_median,
        "speedup": cold_median / warm_median,
        "retained_array_bytes": info.retained_array_bytes,
        "max_array_bytes": info.max_array_bytes,
    }


def main() -> None:
    rng = np.random.default_rng(20260720)
    localized = np.mod(0.25 + 0.015 * rng.normal(size=(300, 3)), 1.0)
    broad = rng.random((300, 3))
    result = {
        "schema_version": "mdstats.density-sparse-optimization-benchmark.v1",
        "fixtures": [
            _field_case("localized", localized),
            _field_case("broad", broad),
        ],
        "support_cache": _cache_case(),
        "notes": [
            "Cache is cleared before each uncached field timing.",
            "Support-cache cold and warm calls are measured separately.",
            "Wall time is platform-specific; numerical equality is also reported.",
        ],
    }
    JSON_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# LD5 sparse density optimization benchmark",
        "",
        "| Fixture | Samples | Active nodes | Kernel pairs | Reference median (s) | Optimized median (s) | Speedup | Rel. L1 error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for fixture in result["fixtures"]:
        lines.append(
            "| {name} | {sample_count} | {active_node_count} | {kernel_pair_count} | "
            "{reference_median_seconds:.6f} | {optimized_median_seconds:.6f} | "
            "{speedup:.2f}x | {relative_l1_error:.3e} |".format(**fixture)
        )
    cache = result["support_cache"]
    lines.extend(
        [
            "",
            "## Canonical-support cache",
            "",
            f"- Cold median: `{cache['cold_median_seconds']:.6f} s`",
            f"- Warm median: `{cache['warm_median_seconds']:.6f} s`",
            f"- Speedup: `{cache['speedup']:.2f}x`",
            f"- Retained array bytes: `{cache['retained_array_bytes']}`",
            f"- Cache byte limit: `{cache['max_array_bytes']}`",
            "",
            "The timings are evidence for this runtime, not portable unit-test thresholds.",
        ]
    )
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(JSON_PATH)
    print(MD_PATH)


if __name__ == "__main__":
    main()
