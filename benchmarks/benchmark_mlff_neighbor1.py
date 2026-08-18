#!/usr/bin/env python3
"""Reproducible NEIGHBOR1 exact-neighborhood/cache-reuse microbenchmark.

The workload is the deterministic PERFBASE1 synthetic TARGET-DATA2B authority
(6 families, 49,152 witnesses, 3,194,880 exact edges).  Scientific digests are
the acceptance oracle; timing is execution evidence only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import statistics
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "benchmarks") not in sys.path:
    sys.path.insert(0, str(ROOT / "benchmarks"))

import mdstats  # noqa: E402
import benchmark_mlff_perfbase1 as perfbase1  # noqa: E402


def _trial(*, workers: int, block_size: int, repeat_index: int) -> dict[str, Any]:
    reference, role = perfbase1._synthetic_reference()
    cpu0 = time.process_time()
    wall0 = time.perf_counter()

    started = time.perf_counter()
    feasibility, neighborhoods = mdstats.build_target_coverage_feasibility_artifacts(
        reference,
        role,
        query_workers=1,
        query_block_size=block_size,
        block_workers=workers,
    )
    feasibility_seconds = time.perf_counter() - started

    started = time.perf_counter()
    index = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        query_workers=1,
        query_block_size=block_size,
    )
    cache_hit_mvidx_seconds = time.perf_counter() - started

    total_seconds = time.perf_counter() - wall0
    cpu_seconds = time.process_time() - cpu0
    edges = sum(family.edge_count for domain in index.domains for family in domain.families)
    witnesses = sum(family.witness_count for domain in neighborhoods.domains for family in domain.families)
    return {
        "workers": int(workers),
        "block_size": int(block_size),
        "repeat_index": int(repeat_index),
        "feasibility_plus_csr_seconds": feasibility_seconds,
        "cache_hit_mvidx_seconds": cache_hit_mvidx_seconds,
        "total_feas_to_mvidx_seconds": total_seconds,
        "process_cpu_seconds": cpu_seconds,
        "maxrss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "feasibility_digest": feasibility.content_digest,
        "neighborhood_digest": neighborhoods.content_digest,
        "sparse_index_digest": index.content_digest,
        "witnesses": int(witnesses),
        "edges": int(edges),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def med(key: str) -> float:
        return float(statistics.median(float(row[key]) for row in rows))

    return {
        "repeat_count": len(rows),
        "workers": int(rows[0]["workers"]),
        "median_feasibility_plus_csr_seconds": med("feasibility_plus_csr_seconds"),
        "median_cache_hit_mvidx_seconds": med("cache_hit_mvidx_seconds"),
        "median_total_feas_to_mvidx_seconds": med("total_feas_to_mvidx_seconds"),
        "median_process_cpu_seconds": med("process_cpu_seconds"),
        "peak_maxrss_kib": max(int(row["maxrss_kib"]) for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 3])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--block-size", type=int, default=512)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 1 or args.warmups < 0 or args.block_size < 1 or any(w < 1 for w in args.workers):
        parser.error("workers/repeats/block-size must be positive and warmups non-negative")

    trials: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    for workers in args.workers:
        for warmup in range(args.warmups):
            _trial(workers=workers, block_size=args.block_size, repeat_index=-(warmup + 1))
        rows = [
            _trial(workers=workers, block_size=args.block_size, repeat_index=repeat)
            for repeat in range(args.repeats)
        ]
        trials.extend(rows)
        summaries[str(workers)] = _summary(rows)

    feasibility_digests = sorted({row["feasibility_digest"] for row in trials})
    neighborhood_digests = sorted({row["neighborhood_digest"] for row in trials})
    index_digests = sorted({row["sparse_index_digest"] for row in trials})
    payload = {
        "schema": "mdstats.mlff-neighbor1-benchmark.v1",
        "release": mdstats.__version__,
        "scientific_equivalence": {
            "feasibility_digest_count": len(feasibility_digests),
            "feasibility_digests": feasibility_digests,
            "neighborhood_digest_count": len(neighborhood_digests),
            "neighborhood_digests": neighborhood_digests,
            "sparse_index_digest_count": len(index_digests),
            "sparse_index_digests": index_digests,
        },
        "workload": {
            "source": "PERFBASE1 deterministic synthetic TARGET-DATA2B authority",
            "family_count": 6,
            "witness_count": 49152,
            "edge_count": 3194880,
            "block_size": args.block_size,
        },
        "summaries": summaries,
        "trials": trials,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
