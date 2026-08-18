#!/usr/bin/env python3
"""Run a bounded read-only MVSEL2 Phase-A production preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import sqlite3
import subprocess
import time

import numpy as np

from mdstats.training_data.target_coverage_sparse_index_store import (
    read_target_coverage_sparse_index_forward_view_native_record,
)
from mdstats.training_data.target_coverage_store import read_target_coverage_native_record
from mdstats.training_data.target_multi_view_selector_v2 import (
    build_target_multi_view_forward_state_v2,
    choose_target_multi_view_phase_a_candidate_v2,
    select_target_multi_view_candidate_v2,
)


def _record_pointer(database: Path, key: str) -> dict[str, object]:
    uri = f"file:{database.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        row = connection.execute(
            "SELECT payload FROM records WHERE key=?", (key,)
        ).fetchone()
    if row is None:
        raise RuntimeError(f"campaign record is missing: {key}")
    payload = json.loads(row[0])
    if not isinstance(payload, dict):
        raise RuntimeError(f"campaign record is not a pointer: {key}")
    return payload


def _rss_kib() -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_database", type=Path)
    parser.add_argument("--domain", default="target")
    parser.add_argument("--campaign-label", default="LTA/mpa0/FP32")
    parser.add_argument("--sample-ranks", type=int, default=3)
    parser.add_argument("--target-size", type=int, default=16384)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--workplan-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.sample_ranks < 1 or args.target_size < 1:
        raise SystemExit("sample-ranks and target-size must be positive")

    state_root = args.campaign_database.resolve().parent
    reference_pointer = _record_pointer(args.campaign_database, "target_coverage_reference")
    index_pointer = _record_pointer(args.campaign_database, "target_coverage_sparse_index")
    started = time.perf_counter()
    reference = read_target_coverage_native_record(reference_pointer, state_root)
    after_reference = time.perf_counter()
    forward_index = read_target_coverage_sparse_index_forward_view_native_record(
        index_pointer, state_root
    )
    after_index = time.perf_counter()
    reference_domain = reference.domain(args.domain)
    forward_domain = forward_index.domain(args.domain)
    state = build_target_multi_view_forward_state_v2(
        reference_domain,
        forward_domain,
        requested_cardinality=args.target_size,
    )
    after_state = time.perf_counter()

    ranks: list[dict[str, object]] = []
    for rank in range(args.sample_ranks):
        rank_started = time.perf_counter()
        choice = choose_target_multi_view_phase_a_candidate_v2(
            reference_domain,
            forward_domain,
            state,
        )
        after_choose = time.perf_counter()
        mutation_edges = sum(
            len(family.candidate_witness_indices(choice.candidate_index))
            for family in forward_domain.families
        ) + len(forward_domain.candidate_obligation_indices(choice.candidate_index))
        select_target_multi_view_candidate_v2(
            choice.candidate_index,
            forward_domain,
            state,
            score=choice.score,
        )
        after_mutation = time.perf_counter()
        ranks.append(
            {
                "rank": rank,
                "candidate_index": choice.candidate_index,
                "frame_uid": reference_domain.frame_uids[choice.candidate_index],
                "bottleneck_family_id": choice.bottleneck_family_id,
                "choose_seconds": after_choose - rank_started,
                "mutation_seconds": after_mutation - after_choose,
                "accepted_rank_seconds": after_mutation - rank_started,
                "mutation_forward_edges": int(mutation_edges),
                "candidate_evaluation_forward_edges": choice.telemetry.candidate_evaluation_forward_edges,
                "eligible_count": choice.telemetry.eligible_count,
                "bottleneck_contender_count": choice.telemetry.bottleneck_contender_count,
                "total_coverage_contender_count": choice.telemetry.total_coverage_contender_count,
                "correlation_contender_count": choice.telemetry.correlation_contender_count,
                "representative_contender_count": choice.telemetry.representative_contender_count,
                "final_contender_count": choice.telemetry.final_contender_count,
                "rss_kib": _rss_kib(),
            }
        )

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    baseline_initialization = float(baseline["optimized"]["initialization_seconds"])
    baseline_rank = float(baseline["optimized"]["rank_0_update_seconds"])
    conservative_rank_seconds = max(float(item["accepted_rank_seconds"]) for item in ranks)
    cold_preflight_seconds = after_state - started
    baseline_full_projection = baseline_initialization + args.target_size * baseline_rank
    v2_full_projection = cold_preflight_seconds + args.target_size * conservative_rank_seconds
    projected_speedup = baseline_full_projection / v2_full_projection
    git_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    payload = {
        "schema": "mdstats.benchmark.mvsel2-phase-a-preflight.v1",
        "workplan": {
            "workplan_id": "DOC-MVSEL2",
            "plan_revision": 4,
            "workplan_sha256": args.workplan_sha256,
        },
        "source": {"git_head": git_head, "selector_version": "MVSEL2-FWD1/PHASEA1"},
        "input": {
            "campaign": str(args.campaign_label),
            "mvidx1_content_digest": forward_index.mvidx1_content_digest,
            "candidate_count": forward_domain.candidate_count,
            "family_count": len(forward_domain.families),
            "forward_edge_count": int(sum(item.edge_count for item in forward_domain.families)),
            "sample_ranks": args.sample_ranks,
            "projection_target_size": args.target_size,
        },
        "cold_preflight": {
            "reference_restore_seconds": after_reference - started,
            "forward_index_restore_seconds": after_index - after_reference,
            "state_validation_build_seconds": after_state - after_index,
            "total_seconds": cold_preflight_seconds,
        },
        "ranks": ranks,
        "projection": {
            "method": "conservative maximum sampled accepted-rank wall time multiplied by identical target cardinality",
            "baseline_initialization_seconds": baseline_initialization,
            "baseline_rank_seconds": baseline_rank,
            "baseline_full_order_seconds": baseline_full_projection,
            "mvsel2_conservative_rank_seconds": conservative_rank_seconds,
            "mvsel2_full_order_seconds": v2_full_projection,
            "projected_speedup": projected_speedup,
            "phase_a_10x_preflight_pass": projected_speedup >= 10.0,
        },
        "resources": {
            "current_rss_kib": _rss_kib(),
            "process_peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "cpu_workers": 1,
            "gpu_used": False,
        },
        "limitations": {
            "full_phase_a_executed": False,
            "projection_is_sla": False,
            "inverse_arrays_mapped": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["projection"], indent=2, sort_keys=True))
    return 0 if projected_speedup >= 10.0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
