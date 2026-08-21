#!/usr/bin/env python3
"""Bounded real-product meter for DOC-REPAIR2-PERF1 staged optimization.

This benchmark consumes authenticated TARGET-DATA2B/MVIDX1/MVSEL2 campaign
products, executes the canonical REPAIR2 owner, and emits execution-only
telemetry. The optional bounded stop is benchmark-private and fires only after
one complete proposal-bearing rung; it never changes product semantics or
persists repair authority.

The filename is retained for compatibility with R0 commands. Summary handling
is version-aware: R0 telemetry used a nested frontier timer, while R1+ reports
state-invariant frontier wall exclusive of representative/objective wall.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import sqlite3
import subprocess
import time
from typing import Any

import mdstats
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.progress_timing import format_progress_time
from mdstats.training_data.target_coverage_sparse_index_store import (
    read_target_coverage_sparse_index_forward_view_native_record,
    read_target_coverage_sparse_index_native_record,
)
from mdstats.training_data.target_coverage_store import read_target_coverage_native_record
from mdstats.training_data.target_multi_view_repair_v2 import (
    TargetMultiViewRepairPolicyV2,
    build_target_multi_view_repair_plan_v2,
    validate_target_multi_view_repair_authority_v2,
)


class _BoundedMeterComplete(RuntimeError):
    pass


def _pointer(database: Path, key: str) -> dict[str, object]:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
    if row is None:
        raise RuntimeError(f"missing campaign record: {key}")
    payload = json.loads(row[0])
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid campaign record: {key}")
    return payload


def _usage() -> dict[str, int]:
    value = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "minor_faults": int(value.ru_minflt),
        "major_faults": int(value.ru_majflt),
        "filesystem_inputs": int(value.ru_inblock),
        "filesystem_outputs": int(value.ru_oublock),
        "peak_rss_kib": int(value.ru_maxrss),
    }


def _usage_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    result = {
        key: after[key] - before[key]
        for key in ("minor_faults", "major_faults", "filesystem_inputs", "filesystem_outputs")
    }
    result["peak_rss_kib"] = after["peak_rss_kib"]
    return result


def _vm_status_kib(name: str) -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _summaries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for event in events:
        if event.get("kind") != "repair_state":
            continue
        key = (str(event["domain"]), int(event["target_size"]))
        row = rows.setdefault(key, {
            "domain": key[0],
            "target_size": key[1],
            "state_iterations": 0,
            "proposals": 0,
            "proposal_evaluations": 0,
            "frontier_builds": 0,
            "accepted_swaps": 0,
            "removal_metric_scan_wall_seconds": 0.0,
            "representative_objective_wall_seconds": 0.0,
            "proposal_frontier_state_invariant_inclusive_wall_seconds": 0.0,
            "proposal_frontier_state_invariant_exclusive_wall_seconds": 0.0,
            "removal_dependent_representative_diversity_wall_seconds": 0.0,
            "accepted_mutation_wall_seconds": 0.0,
            "removal_metric_candidate_family_rows": 0,
            "removal_metric_forward_edges": 0,
            "coverage_gain_candidate_family_rows": 0,
            "coverage_gain_forward_edges": 0,
            "frontier_coverage_gain_candidate_family_rows": 0,
            "frontier_coverage_gain_forward_edges": 0,
            "proposal_final_coverage_candidate_family_rows": 0,
            "proposal_final_coverage_forward_edges": 0,
            "telemetry_regimes": [],
        })
        row["state_iterations"] += 1
        row["proposals"] += int(event["proposal_count"])
        row["accepted_swaps"] += int(event["accepted_swaps"])

        is_r1 = "frontier_build_count" in event
        regime = "r1_frontier_timer_exclusive" if is_r1 else "r0_frontier_timer_inclusive"
        if regime not in row["telemetry_regimes"]:
            row["telemetry_regimes"].append(regime)
        row["frontier_builds"] += int(event.get("frontier_build_count", 0))
        row["proposal_evaluations"] += int(
            event.get("proposal_evaluation_count", event["proposal_count"])
        )

        for name in (
            "removal_metric_candidate_family_rows",
            "removal_metric_forward_edges",
            "coverage_gain_candidate_family_rows",
            "coverage_gain_forward_edges",
            "frontier_coverage_gain_candidate_family_rows",
            "frontier_coverage_gain_forward_edges",
            "proposal_final_coverage_candidate_family_rows",
            "proposal_final_coverage_forward_edges",
        ):
            row[name] += int(event.get(name, 0))
        for name in (
            "removal_metric_scan_wall_seconds",
            "representative_objective_wall_seconds",
            "removal_dependent_representative_diversity_wall_seconds",
            "accepted_mutation_wall_seconds",
        ):
            row[name] += float(event[name])

        frontier = float(event["proposal_frontier_state_invariant_wall_seconds"])
        representative = float(event["representative_objective_wall_seconds"])
        if is_r1:
            # R1 source measures the shared frontier interval after subtracting
            # the separately measured representative/objective interval.
            exclusive = frontier
            inclusive = frontier + representative
        else:
            # R0 source nested representative/objective timing inside the raw
            # frontier timer. Preserve the old correction for existing R0 JSON.
            inclusive = frontier
            exclusive = max(0.0, frontier - representative)
        row["proposal_frontier_state_invariant_inclusive_wall_seconds"] += inclusive
        row["proposal_frontier_state_invariant_exclusive_wall_seconds"] += exclusive
    for row in rows.values():
        row["telemetry_regimes"] = tuple(row["telemetry_regimes"])
    return [rows[key] for key in sorted(rows)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_database", type=Path)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-candidate-count", type=int, default=36408)
    parser.add_argument("--expected-family-count", type=int, default=165)
    parser.add_argument("--stop-after-first-proposal-rung", action="store_true")
    parser.add_argument("--validate-full-result", action="store_true")
    args = parser.parse_args()

    database = args.campaign_database.resolve()
    root = database.parent
    reference_pointer = _pointer(database, "target_coverage_reference")
    sparse_pointer = _pointer(database, "target_coverage_sparse_index")
    reference = read_target_coverage_native_record(reference_pointer, root)
    forward = read_target_coverage_sparse_index_forward_view_native_record(sparse_pointer, root)
    reference_domain = reference.domain(args.domain)
    forward_domain = forward.domain(args.domain)
    if forward_domain.candidate_count != args.expected_candidate_count:
        raise RuntimeError(
            f"candidate-count mismatch: expected={args.expected_candidate_count} "
            f"actual={forward_domain.candidate_count}"
        )
    if len(forward_domain.families) != args.expected_family_count:
        raise RuntimeError(
            f"family-count mismatch: expected={args.expected_family_count} "
            f"actual={len(forward_domain.families)}"
        )

    store = CampaignStore(database)
    try:
        selection = store.get_record_optional(
            "target_multi_view_selection_v2", mdstats.TargetMultiViewSelectionPlanV2
        )
        if selection is None:
            raise RuntimeError("campaign has no authenticated target_multi_view_selection_v2 authority")
    finally:
        store.close()
    selection.domain(args.domain)

    policy = TargetMultiViewRepairPolicyV2()
    events: list[dict[str, Any]] = []
    bounded_stop: dict[str, Any] | None = None

    def telemetry(event: dict[str, Any]) -> None:
        nonlocal bounded_stop
        events.append(dict(event))
        if event.get("kind") == "repair_state":
            print(
                "[REPAIR2-PERF1] "
                f"domain={event['domain']}; target_size={event['target_size']}; "
                f"state={event['state_iteration']}; proposals={event['proposal_count']}; "
                f"frontier={event['proposal_frontier_state_invariant_wall_hhmmss']}; "
                f"coverage_edges={event['coverage_gain_forward_edges']}",
                flush=True,
            )
        if (
            args.stop_after_first_proposal_rung
            and event.get("kind") == "rung"
            and int(event.get("rung_proposal_count", 0)) > 0
        ):
            bounded_stop = dict(event)
            raise _BoundedMeterComplete

    started = time.perf_counter()
    usage_before = _usage()
    rss_before = _vm_status_kib("VmRSS")
    swap_before = _vm_status_kib("VmSwap")
    repair = None
    completed = False
    try:
        repair = build_target_multi_view_repair_plan_v2(
            reference,
            forward,
            selection,
            policy=policy,
            workers=1,
            progress_callback=lambda message: print(f"[REPAIR2-PERF1] {message}", flush=True),
            telemetry_callback=telemetry,
        )
        completed = True
    except _BoundedMeterComplete:
        pass
    build_wall = time.perf_counter() - started
    usage_after = _usage()

    validation_wall = None
    validation_usage = None
    if completed and repair is not None and args.validate_full_result:
        full_sparse = read_target_coverage_sparse_index_native_record(sparse_pointer, root)
        validation_before = _usage()
        validation_started = time.perf_counter()
        validate_target_multi_view_repair_authority_v2(
            repair,
            target_coverage_reference=reference,
            target_coverage_sparse_index=full_sparse,
            target_multi_view_selection=selection,
        )
        validation_wall = time.perf_counter() - validation_started
        validation_usage = _usage_delta(validation_before, _usage())

    payload = {
        "schema": "mdstats.benchmark.repair2-perf1.v2",
        "source": {"git_head": _git_head()},
        "input": {
            "campaign_database": str(database),
            "domain": args.domain,
            "dataset_id": reference.dataset_id,
            "reference_digest": reference.content_digest,
            "mvidx1_digest": forward.mvidx1_content_digest,
            "selection_digest": selection.content_digest,
            "candidate_count": forward_domain.candidate_count,
            "family_count": len(forward_domain.families),
            "forward_edge_count": int(sum(family.edge_count for family in forward_domain.families)),
        },
        "execution": {
            "workers": 1,
            "policy": policy.to_dict(),
            "completed_full_repair": completed,
            "bounded_stop_requested": args.stop_after_first_proposal_rung,
            "bounded_stop_rung": bounded_stop,
            "build_wall_seconds": build_wall,
            "build_wall_hhmmss": format_progress_time(build_wall),
            "build_resource_delta": _usage_delta(usage_before, usage_after),
            "process_rss_kib_before": rss_before,
            "process_rss_kib_after": _vm_status_kib("VmRSS"),
            "process_swap_kib_before": swap_before,
            "process_swap_kib_after": _vm_status_kib("VmSwap"),
            "repair_content_digest": None if repair is None else repair.content_digest,
            "validation_requested": args.validate_full_result,
            "validation_passed": True if validation_wall is not None else None,
            "validation_wall_seconds": validation_wall,
            "validation_wall_hhmmss": None if validation_wall is None else format_progress_time(validation_wall),
            "validation_resource_delta": validation_usage,
        },
        "rung_events": [event for event in events if event.get("kind") == "rung"],
        "state_summary": _summaries(events),
        "telemetry_events": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "completed_full_repair": completed,
                "bounded_stop_rung": None if bounded_stop is None else bounded_stop.get("target_size"),
                "build_wall_seconds": build_wall,
                "output": str(args.output),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
