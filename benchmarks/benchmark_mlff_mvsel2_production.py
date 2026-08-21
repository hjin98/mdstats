#!/usr/bin/env python3
"""Production-density MVSEL2 selector qualification through Phase B."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import resource
import sqlite3
import subprocess
import time

from mdstats.training_data.target_coverage_sparse_index_store import (
    read_target_coverage_sparse_index_forward_view_native_record,
)
from mdstats.training_data.target_coverage_store import read_target_coverage_native_record
from mdstats.training_data.target_multi_view_selector_v2 import (
    build_target_multi_view_forward_state_v2,
    build_target_multi_view_lazy_frontier_v2,
    choose_target_multi_view_phase_a_candidate_v2,
    choose_target_multi_view_phase_b_candidate_v2,
    select_target_multi_view_candidate_v2,
    release_target_multi_view_forward_pages_v2,
)


def _pointer(database: Path, key: str) -> dict[str, object]:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
    if row is None:
        raise RuntimeError(f"missing campaign record: {key}")
    payload = json.loads(row[0])
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid campaign record: {key}")
    return payload


def _rss_kib() -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_database", type=Path)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--campaign-label", default="LTA/mpa0/FP32")
    parser.add_argument("--phase-b-ranks", type=int, default=32)
    parser.add_argument("--target-size", type=int, default=16384)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--workplan-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign_database.resolve().parent
    reference_pointer = _pointer(args.campaign_database, "target_coverage_reference")
    index_pointer = _pointer(args.campaign_database, "target_coverage_sparse_index")

    start = time.perf_counter()
    reference = read_target_coverage_native_record(reference_pointer, root)
    reference_seconds = time.perf_counter() - start
    first = time.perf_counter()
    forward_index = read_target_coverage_sparse_index_forward_view_native_record(index_pointer, root)
    first_restore_seconds = time.perf_counter() - first
    del forward_index
    gc.collect()
    second = time.perf_counter()
    forward_index = read_target_coverage_sparse_index_forward_view_native_record(index_pointer, root)
    repeated_restore_seconds = time.perf_counter() - second

    reference_domain = reference.domain(args.domain)
    forward_domain = forward_index.domain(args.domain)
    state_start = time.perf_counter()
    state = build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain, requested_cardinality=args.target_size
    )
    state_seconds = time.perf_counter() - state_start
    phase_a_started = time.perf_counter()
    phase_a_rows: list[dict[str, object]] = []
    while state.unsatisfied_required_obligation_count > 0 or any(
        family.coverage_mass < 0.95 - 1.0e-14 for family in state.family_states
    ):
        rank_started = time.perf_counter()
        choice = choose_target_multi_view_phase_a_candidate_v2(
            reference_domain, forward_domain, state
        )
        choose_seconds = time.perf_counter() - rank_started
        mutation_edges = sum(
            len(family.candidate_witness_indices(choice.candidate_index))
            for family in forward_domain.families
        ) + len(forward_domain.candidate_obligation_indices(choice.candidate_index))
        mutation_started = time.perf_counter()
        select_target_multi_view_candidate_v2(
            choice.candidate_index, forward_domain, state, score=choice.score
        )
        row = {
            "rank": state.selected_count - 1,
            "choose_seconds": choose_seconds,
            "mutation_seconds": time.perf_counter() - mutation_started,
            "candidate_evaluation_forward_edges": choice.telemetry.candidate_evaluation_forward_edges,
            "mutation_forward_edges": int(mutation_edges),
            "eligible_count": choice.telemetry.eligible_count,
            "contender_width": choice.telemetry.final_contender_count,
        }
        phase_a_rows.append(row)
        if state.selected_count == 1 or state.selected_count % 25 == 0:
            print(
                f"phase_a rank={state.selected_count} elapsed={time.perf_counter()-phase_a_started:.1f}s "
                f"choose={choose_seconds:.3f}s rss_kib={_rss_kib()}",
                flush=True,
            )
    phase_a_seconds = time.perf_counter() - phase_a_started
    release_target_multi_view_forward_pages_v2(forward_domain)
    phase_a_post_release_rss_kib = _rss_kib()

    rebase_started = time.perf_counter()
    frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, state)
    rebase_seconds = time.perf_counter() - rebase_started
    phase_b_rows: list[dict[str, object]] = []
    consecutive_fallback = 0
    maximum_consecutive_fallback = 0
    for _ in range(min(args.phase_b_ranks, args.target_size - state.selected_count)):
        rank_started = time.perf_counter()
        choice = choose_target_multi_view_phase_b_candidate_v2(
            reference_domain, forward_domain, state, frontier
        )
        choose_seconds = time.perf_counter() - rank_started
        mutation_edges = sum(
            len(family.candidate_witness_indices(choice.candidate_index))
            for family in forward_domain.families
        ) + len(forward_domain.candidate_obligation_indices(choice.candidate_index))
        mutation_started = time.perf_counter()
        select_target_multi_view_candidate_v2(
            choice.candidate_index, forward_domain, state, score=choice.score
        )
        fallback = bool(choice.telemetry.fallback_used)
        consecutive_fallback = consecutive_fallback + 1 if fallback else 0
        maximum_consecutive_fallback = max(maximum_consecutive_fallback, consecutive_fallback)
        phase_b_rows.append({
            "rank": state.selected_count - 1,
            "choose_seconds": choose_seconds,
            "mutation_seconds": time.perf_counter() - mutation_started,
            "certified_frontier_width": choice.telemetry.certified_frontier_width,
            "rescoring_count": choice.telemetry.rescoring_count,
            "representative_evaluation_forward_edges": choice.telemetry.representative_evaluation_edges,
            "diversity_evaluation_forward_edges": choice.telemetry.diversity_evaluation_edges,
            "mutation_forward_edges": int(mutation_edges),
            "heap_entries": choice.telemetry.heap_entries,
            "fallback_used": fallback,
        })
        print(
            f"phase_b rank={state.selected_count} choose={choose_seconds:.3f}s "
            f"rescores={choice.telemetry.rescoring_count} frontier={choice.telemetry.certified_frontier_width}",
            flush=True,
        )

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    baseline_full = float(baseline["optimized"]["initialization_seconds"]) + args.target_size * float(
        baseline["optimized"]["rank_0_update_seconds"]
    )
    phase_b_max = max(float(row["choose_seconds"]) + float(row["mutation_seconds"]) for row in phase_b_rows)
    remaining = max(0, args.target_size - len(phase_a_rows))
    projected = (
        reference_seconds + first_restore_seconds + state_seconds + phase_a_seconds
        + rebase_seconds + remaining * phase_b_max
    )
    fallback_count = sum(bool(row["fallback_used"]) for row in phase_b_rows)
    payload = {
        "schema": "mdstats.benchmark.mvsel2-production-density.v1",
        "workplan": {"workplan_id": "DOC-MVSEL2", "plan_revision": 4, "workplan_sha256": args.workplan_sha256},
        "source": {"git_head": subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()},
        "input": {
            "campaign": args.campaign_label,
            "mvidx1_content_digest": forward_index.mvidx1_content_digest,
            "candidate_count": forward_domain.candidate_count,
            "family_count": len(forward_domain.families),
            "forward_edge_count": int(sum(family.edge_count for family in forward_domain.families)),
            "target_size": args.target_size,
        },
        "index_io": {
            "first_process_restore_seconds": first_restore_seconds,
            "repeated_process_restore_seconds": repeated_restore_seconds,
            "os_page_cache_controlled": False,
            "inverse_arrays_mapped": False,
        },
        "phase_a": {
            "accepted_ranks": len(phase_a_rows),
            "seconds": phase_a_seconds,
            "max_rank_seconds": max(float(row["choose_seconds"]) + float(row["mutation_seconds"]) for row in phase_a_rows),
            "post_release_rss_kib": phase_a_post_release_rss_kib,
            "rows": phase_a_rows,
        },
        "phase_b": {
            "exact_rebase_seconds": rebase_seconds,
            "sampled_ranks": len(phase_b_rows),
            "max_rank_seconds": phase_b_max,
            "fallback_count": fallback_count,
            "fallback_fraction": 0.0 if not phase_b_rows else fallback_count / len(phase_b_rows),
            "maximum_consecutive_fallback": maximum_consecutive_fallback,
            "post_rebase_release_rss_kib": _rss_kib(),
            "rows": phase_b_rows,
        },
        "projection": {
            "baseline_full_order_seconds": baseline_full,
            "mvsel2_full_order_seconds": projected,
            "projected_speedup": baseline_full / projected,
            "minimum_10x_pass": baseline_full / projected >= 10.0,
            "method": "measured complete Phase A plus exact rebase plus conservative maximum sampled Phase-B rank",
        },
        "resources": {
            "current_rss_kib": _rss_kib(),
            "process_peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            "cpu_workers": 1,
            "gpu_used": False,
        },
        "selected_candidate_order": list(state.selected_order),
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"phase_a": payload["phase_a"] | {"rows": "omitted"}, "phase_b": payload["phase_b"] | {"rows": "omitted"}, "projection": payload["projection"], "resources": payload["resources"]}, indent=2), flush=True)
    passed = (
        payload["projection"]["minimum_10x_pass"]
        and fallback_count <= 0.01 * max(1, len(phase_b_rows))
        and maximum_consecutive_fallback <= 3
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
