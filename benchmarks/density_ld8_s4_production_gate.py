#!/usr/bin/env python3
"""Run the LD8-S4 four-species normal-dispatch production gate."""
from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
import threading
import time
from pathlib import Path
from typing import Any

import cloudpickle
import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from density_ld8_p0_benchmark import _resolution_options, _scene_field_samples
from mdstats.plotting.atomic_density import (
    _prepare_sparse_field_for_options,
    resolve_density_numerics,
)
from mdstats.plotting.density_contracts import DensityOptimizationOptions

SCHEMA = "mdstats.density-ld8-s4-production-gate.v1"
BASELINE_SCIENTIFIC_SECONDS = 339.686
MAX_AGGREGATE_SECONDS = 120.0
MIN_SPEEDUP = 3.0
MAX_CHANNEL_PEAK_RSS_BYTES = int(1.5 * 2**30)


class PeakRSS:
    def __init__(self, interval: float = 0.02) -> None:
        self.process = psutil.Process()
        self.interval = interval
        self.peak = self.process.memory_info().rss
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

    def __enter__(self):
        def sample() -> None:
            while not self.stop.wait(self.interval):
                self.peak = max(self.peak, self.process.memory_info().rss)
        self.thread = threading.Thread(target=sample, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.peak = max(self.peak, self.process.memory_info().rss)
        self.stop.set()
        if self.thread is not None:
            self.thread.join()


def _md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# LD8-S4 production gate",
        "",
        f"- Aggregate scientific time: `{payload['aggregate_scientific_seconds']:.3f} s`",
        f"- Speedup over LD7: `{payload['aggregate_speedup_over_ld7']:.2f}x`",
        f"- Gate passed: `{payload['gate_passed']}`",
        "",
        "| Field | Grid | Scientific | HDR | Blocks | Nodes | D/F tiles | Peak RSS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["fields"]:
        lines.append(
            "| {label} | {grid} | {seconds:.3f} s | {hdr:.3f} s | {blocks} | {nodes} | {direct}/{fft} | {rss:.3f} GiB |".format(
                label=row["label"],
                grid="x".join(map(str, row["grid_shape"])),
                seconds=row["scientific_seconds"],
                hdr=row["multi_hdr_seconds"],
                blocks=row["active_block_count"],
                nodes=row["nonzero_node_count"],
                direct=row["direct_tile_count"],
                fft=row["fft_tile_count"],
                rss=row["peak_rss_bytes"] / 2**30,
            )
        )
    lines += ["", "## Gate checks", ""]
    for key, value in payload["gate_checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    with args.scene.open("rb") as handle:
        scene = cloudpickle.load(handle)
    fields = list(scene.atomic_density_fields)
    if args.labels:
        requested = set(args.labels)
        fields = [field for field in fields if field.label in requested]
    rows: list[dict[str, Any]] = []
    started_all = time.perf_counter()
    for field in fields:
        gc.collect()
        fractional, samples = _scene_field_samples(scene, field, None)
        frame_weights = np.full(fractional.shape[0], 1.0 / fractional.shape[0])
        options = _resolution_options(args.kernel_tail_tolerance)
        options = type(options)(
            resolution_options=options.resolution_options,
            kernel_options=options.kernel_options,
            storage_options=options.storage_options,
            optimization_options=DensityOptimizationOptions(
                sparse_evaluation_mode="optimized",
                cache_stencil_supports=True,
                sparse_pair_chunk_size=args.pair_chunk_size,
                sparse_group_batch_size=8,
                sparse_realization_mode="hybrid",
                allow_ld7_fallback=False,
                hybrid_compute_tile_shape=tuple(args.tile_shape),
                hybrid_min_fft_source_nodes=args.min_fft_source_nodes,
                hybrid_fft_workers=args.fft_workers,
            ),
        )
        t = time.perf_counter()
        numerics = resolve_density_numerics(
            scene.display_cell,
            options=options,
            fractional_by_frame=fractional,
            frame_weights=frame_weights,
            pbc=np.ones(3, dtype=bool),
            max_voxels=np.iinfo(np.int64).max,
            field_label=field.label,
        )
        resolution_seconds = time.perf_counter() - t
        with PeakRSS() as monitor:
            t = time.perf_counter()
            realized = _prepare_sparse_field_for_options(
                samples,
                grid_shape=numerics.grid_shape,
                display_cell=scene.display_cell,
                gaussian_bandwidth=numerics.gaussian_bandwidth,
                field_key=field.field_key,
                label=field.label,
                physical_units=field.physical_units,
                broadening_metric=options.resolution_options.broadening_metric,
                options=options,
                selected_atom_indices=tuple(field.selected_atom_indices),
                metadata={"benchmark": SCHEMA},
                max_cic_contributions=100_000_000,
                max_kernel_pairs=20_000_000_000,
                max_workspace_bytes=2_000_000_000,
                max_nonzero_nodes=100_000_000,
                max_stored_block_values=100_000_000,
                max_blocks=2_000_000,
                max_planning_bytes=2_000_000_000,
            )
            scientific_seconds = time.perf_counter() - t
        t = time.perf_counter()
        hdr = realized.hdr_details_many((0.50, 0.80, 0.95))
        multi_hdr_seconds = time.perf_counter() - t
        t = time.perf_counter()
        contour = realized.contour_support_many((0.50, 0.80, 0.95), compute_components=True)
        contour_seconds = time.perf_counter() - t
        row = {
            "field_key": field.field_key,
            "label": field.label,
            "grid_shape": list(numerics.grid_shape),
            "gaussian_bandwidth": numerics.gaussian_bandwidth,
            "resolution_seconds": resolution_seconds,
            "scientific_seconds": scientific_seconds,
            "multi_hdr_seconds": multi_hdr_seconds,
            "contour_support_seconds": contour_seconds,
            "integral": realized.integral,
            "total_measure": realized.total_measure,
            "active_block_count": realized.active_block_count,
            "nonzero_node_count": realized.nonzero_node_count,
            "retained_array_bytes": realized.retained_array_bytes,
            "peak_rss_bytes": monitor.peak,
            "direct_tile_count": int(realized.metadata["direct_tile_count"]),
            "fft_tile_count": int(realized.metadata["fft_tile_count"]),
            "fft_nonpositive_node_repairs": int(realized.metadata["fft_nonpositive_node_repairs"]),
            "production_backend": bool(realized.metadata["production_backend"]),
            "fallback_used": bool(realized.metadata.to_json_dict().get("ld8_s4_fallback_used", False)),
            "hdr": hdr.to_json_dict(),
            "contour_support": [item.to_json_dict(include_arrays=False) for item in contour],
        }
        print(
            f"[S4] {field.label}: {scientific_seconds:.3f}s; "
            f"HDR {multi_hdr_seconds:.3f}s; tiles "
            f"{row['direct_tile_count']}/{row['fft_tile_count']}; "
            f"RSS {monitor.peak / 2**30:.3f} GiB",
            flush=True,
        )
        rows.append(row)
        del realized, hdr, contour, samples, fractional
        gc.collect()
    aggregate = float(sum(row["scientific_seconds"] for row in rows))
    speedup = BASELINE_SCIENTIFIC_SECONDS / aggregate
    checks = {
        "all_four_species_present": len(rows) == 4,
        "aggregate_scientific_seconds_le_120": aggregate <= MAX_AGGREGATE_SECONDS,
        "aggregate_speedup_ge_3": speedup >= MIN_SPEEDUP,
        "all_channel_peak_rss_le_1_5_gib": all(row["peak_rss_bytes"] <= MAX_CHANNEL_PEAK_RSS_BYTES for row in rows),
        "all_integrals_exact": all(abs(row["integral"] - row["total_measure"]) <= 5e-13 * max(1.0, row["total_measure"]) for row in rows),
        "all_production_backend": all(row["production_backend"] for row in rows),
        "no_fallback": all(not row["fallback_used"] for row in rows),
        "three_hdr_levels_each": all(len(row["hdr"]["details"]) == 3 for row in rows),
    }
    return {
        "schema": SCHEMA,
        "scene": str(args.scene),
        "kernel_tail_tolerance": args.kernel_tail_tolerance,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "logical_cpu_count": psutil.cpu_count(logical=True),
        },
        "baseline_ld7_scientific_seconds": BASELINE_SCIENTIFIC_SECONDS,
        "aggregate_scientific_seconds": aggregate,
        "aggregate_speedup_over_ld7": speedup,
        "total_wall_seconds": time.perf_counter() - started_all,
        "fields": rows,
        "gate_checks": checks,
        "gate_passed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-markdown", type=Path)
    parser.add_argument("--kernel-tail-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--tile-shape", type=int, nargs=3, default=(32, 32, 32))
    parser.add_argument("--pair-chunk-size", type=int, default=262_144)
    parser.add_argument("--min-fft-source-nodes", type=int, default=32)
    parser.add_argument("--fft-workers", type=int, default=1)
    parser.add_argument("--label", dest="labels", action="append")
    args = parser.parse_args()
    payload = run(args)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _md(payload, args.output_markdown or args.output_json.with_suffix(".md"))
    print(json.dumps({
        "gate_passed": payload["gate_passed"],
        "aggregate_scientific_seconds": payload["aggregate_scientific_seconds"],
        "aggregate_speedup_over_ld7": payload["aggregate_speedup_over_ld7"],
    }, indent=2))
    if not payload["gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
