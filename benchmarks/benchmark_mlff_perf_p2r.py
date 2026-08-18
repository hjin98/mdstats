#!/usr/bin/env python3
"""Bounded CPU/control-plane benchmark for PERF-P2R.

This benchmark intentionally does not execute MACE training or make GPU claims.
It measures the DATA8 immutable fixed-file cache on the deterministic scientific
fixture used by the DATA8 regression suite, and records the exact analytical
successive-fidelity exposure envelope over the complete parameterized coarse
endpoint grid.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import mdstats

from tests.test_mlff_data8_mace_artifacts import _data7_bundles, _foundation, _probe

SCHEMA = "mdstats.perf-p2r-cpu-benchmark.2026-08.v1"
DEFAULT_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192)


def _proc_io() -> dict[str, int]:
    result: dict[str, int] = {}
    try:
        for line in Path("/proc/self/io").read_text().splitlines():
            key, value = line.split(":", 1)
            result[key.strip()] = int(value.strip())
    except (FileNotFoundError, OSError, ValueError):
        pass
    return result


def _sample(build) -> dict[str, Any]:
    io0 = _proc_io()
    cpu0 = time.process_time()
    wall0 = time.perf_counter()
    bundle = build()
    wall = time.perf_counter() - wall0
    cpu = time.process_time() - cpu0
    io1 = _proc_io()
    return {
        "wall_seconds": wall,
        "process_cpu_seconds": cpu,
        "io_delta": {key: io1.get(key, 0) - io0.get(key, 0) for key in sorted(set(io0) | set(io1))},
        "bundle": bundle,
    }


def _summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    wall = [float(item["wall_seconds"]) for item in samples]
    cpu = [float(item["process_cpu_seconds"]) for item in samples]
    return {
        "count": len(samples),
        "wall_seconds": {
            "minimum": min(wall),
            "median": statistics.median(wall),
            "maximum": max(wall),
        },
        "process_cpu_seconds": {
            "minimum": min(cpu),
            "median": statistics.median(cpu),
            "maximum": max(cpu),
        },
        "write_characters_median": statistics.median(
            [int(item["io_delta"].get("wchar", 0)) for item in samples]
        ),
        "read_characters_median": statistics.median(
            [int(item["io_delta"].get("rchar", 0)) for item in samples]
        ),
    }


def _exposure_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for coarse_epoch in (3, 4, 5):
        for width in range(3, 8):
            admitted = DEFAULT_SIZES[:width]
            coarse_count = min(4, width)
            short_count = min(2, coarse_count)
            for survivor_case in ("smallest", "largest"):
                if survivor_case == "smallest":
                    coarse_survivors = admitted[:coarse_count]
                    short_survivors = coarse_survivors[:short_count]
                else:
                    coarse_survivors = admitted[-coarse_count:]
                    short_survivors = coarse_survivors[-short_count:]
                exposure = mdstats.build_perf_p2r_exposure(
                    admissible_sizes=admitted,
                    coarse_survivor_sizes=coarse_survivors,
                    short_finalist_sizes=short_survivors,
                    coarse_training_epochs=coarse_epoch,
                    short_training_epochs=10,
                    final_training_epochs=30,
                )
                rows.append(
                    {
                        "coarse_epoch": coarse_epoch,
                        "admitted_width": width,
                        "survivor_case": survivor_case,
                        "admitted_sizes": list(admitted),
                        "coarse_survivor_sizes": list(coarse_survivors),
                        "short_survivor_sizes": list(short_survivors),
                        "incremental_structure_epochs": exposure.total_structure_epochs,
                        "exhaustive_structure_epochs": exposure.exhaustive_structure_epochs,
                        "saved_fraction": exposure.saved_fraction,
                        "content_digest": exposure.content_digest,
                    }
                )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=15)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error("--repeats must be at least 3")

    with tempfile.TemporaryDirectory(prefix="mdstats-perf-p2r-") as td:
        root = Path(td)
        sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(root)
        foundation = _foundation(root)
        output = root / "data8-output"
        cache = root / "data8-fixed-cache"
        kwargs = dict(
            source_catalog=sources,
            frame_catalog=frames,
            frame_data_by_run=frame_data,
            data5_bundle=data5,
            data7_bundles=bundles,
            output_directory=output,
            foundation_checkpoint=foundation,
            compatibility_probe=_probe(),
            optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
            require_foundation_residual_e0=False,
        )

        fresh_samples: list[dict[str, Any]] = []
        reference_payload = None
        for _ in range(args.repeats):
            shutil.rmtree(output, ignore_errors=True)
            sample = _sample(lambda: mdstats.build_data8_preparation_bundle(**kwargs))
            payload = sample.pop("bundle").to_dict()
            reference_payload = payload
            fresh_samples.append(sample)

        shutil.rmtree(output, ignore_errors=True)
        populate = _sample(
            lambda: mdstats.build_data8_preparation_bundle(
                **kwargs, shared_fixed_file_cache_directory=cache
            )
        )
        populate_payload = populate.pop("bundle").to_dict()
        if populate_payload != reference_payload:
            raise RuntimeError("Cache-population DATA8 authority differs from fresh authority")

        hit_samples: list[dict[str, Any]] = []
        exact = True
        for _ in range(args.repeats):
            shutil.rmtree(output, ignore_errors=True)
            sample = _sample(
                lambda: mdstats.build_data8_preparation_bundle(
                    **kwargs, shared_fixed_file_cache_directory=cache
                )
            )
            payload = sample.pop("bundle").to_dict()
            exact = exact and payload == reference_payload
            hit_samples.append(sample)

        fresh_summary = _summary(fresh_samples)
        hit_summary = _summary(hit_samples)
        fresh_median = fresh_summary["wall_seconds"]["median"]
        hit_median = hit_summary["wall_seconds"]["median"]
        cache_files = [path for path in cache.rglob("*") if path.is_file()]
        cache_bytes = sum(path.stat().st_size for path in cache_files)
        exposure = _exposure_matrix()
        full_width = [item for item in exposure if item["admitted_width"] == 7]
        saved_values = [float(item["saved_fraction"]) for item in full_width]

        result = {
            "schema": SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "mdstats_version": mdstats.__version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_model": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.lower().startswith("model name")
                ),
                "unknown",
            ),
            "logical_cpu_count": os.cpu_count(),
            "benchmark_scope": "cpu_control_plane_only_no_mace_training_no_gpu_claim",
            "fixture": {
                "frame_catalog_digest": frames.content_digest,
                "data5_bundle_digest": data5.content_digest,
                "data7_bundle_digests": [item.content_digest for item in bundles],
                "job_count": len(populate_payload["jobs"]),
            },
            "data8_fixed_file_cache": {
                "repeats": args.repeats,
                "scientific_authority_exact": bool(exact),
                "fresh": fresh_summary,
                "cache_population": {
                    "wall_seconds": populate["wall_seconds"],
                    "process_cpu_seconds": populate["process_cpu_seconds"],
                    "io_delta": populate["io_delta"],
                },
                "cache_hit": hit_summary,
                "median_speedup": fresh_median / hit_median,
                "median_wall_reduction_fraction": 1.0 - hit_median / fresh_median,
                "cache_generation_count": len(list(cache.rglob("cache.json"))),
                "cache_file_count": len(cache_files),
                "cache_bytes": cache_bytes,
            },
            "successive_fidelity_exposure": {
                "formula": "coarse*sum(A) + (10-coarse)*sum(S4) + 20*sum(S2)",
                "rows": exposure,
                "full_width_saved_fraction_min": min(saved_values),
                "full_width_saved_fraction_max": max(saved_values),
            },
            "limitations": [
                "This benchmark does not execute MACE training or inference.",
                "DATA8 timing is a bounded deterministic development fixture, not an LTA production-volume throughput claim.",
                "Whole-funnel GPU/VRAM/utilization and resumed-versus-uninterrupted MACE evidence remain deferred to FINAL-GPU1.",
                "Structure-epoch exposure is an exact work proxy, not a wall-time prediction.",
            ],
        }

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
