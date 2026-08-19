#!/usr/bin/env python3
"""Protocol-v3 production qualification harness for MVSEL2/REPAIR2 hardening.

This harness intentionally does not regenerate selector authority.  It consumes
an authenticated campaign ``target_multi_view_selection_v2`` record, opens the
persisted MVIDX1 through the native forward-only reader, restores compatible
MVSTATE2 rung checkpoints when available, and runs the default REPAIR2 policy
through every materializable fixed-eight rung up to 16,384.

The output is qualification evidence only.  It is not product authority and it
does not update the campaign database.
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
from mdstats.training_data.mvsel2_hardening_runtime import (
    _all_valid_rung_states,
    _build_repair_from_checkpoints,
)
from mdstats.training_data.target_coverage_sparse_index_store import (
    read_target_coverage_sparse_index_forward_view_native_record,
)
from mdstats.training_data.target_coverage_store import (
    read_target_coverage_native_record,
)
from mdstats.training_data.target_multi_view_repair_v2 import (
    TargetMultiViewRepairPolicyV2,
)

_FIXED_EIGHT = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)


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
        return None
    return None


def _fields(message: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in message.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_database", type=Path)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--workplan-id", default="DOC-MVSEL2-HARDEN1-V3")
    parser.add_argument("--workplan-revision", type=int, default=1)
    parser.add_argument("--workplan-sha256", required=True)
    parser.add_argument("--expected-candidate-count", type=int, default=36408)
    parser.add_argument("--expected-family-count", type=int, default=165)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    database = args.campaign_database.resolve()
    root = database.parent
    reference = read_target_coverage_native_record(
        _pointer(database, "target_coverage_reference"), root
    )
    forward = read_target_coverage_sparse_index_forward_view_native_record(
        _pointer(database, "target_coverage_sparse_index"), root
    )
    reference_domain = reference.domain(args.domain)
    forward_domain = forward.domain(args.domain)

    store = CampaignStore(database)
    try:
        selection = store.get_record_optional(
            "target_multi_view_selection_v2", mdstats.TargetMultiViewSelectionPlanV2
        )
        if selection is None:
            raise RuntimeError(
                "campaign has no authenticated target_multi_view_selection_v2 authority"
            )
        selection_domain = selection.domain(args.domain)
        expected_sizes = tuple(
            size for size in _FIXED_EIGHT if size <= forward_domain.candidate_count
        )
        materializable_sizes = tuple(
            int(rung.target_size)
            for rung in selection_domain.rungs
            if rung.materializable and int(rung.target_size) <= 16384
        )
        if materializable_sizes != expected_sizes:
            raise RuntimeError(
                "MVSEL2 materializable production ladder mismatch: "
                f"expected={expected_sizes!r} actual={materializable_sizes!r}"
            )
        if forward_domain.candidate_count != args.expected_candidate_count:
            raise RuntimeError(
                "production candidate-count mismatch: "
                f"expected={args.expected_candidate_count} actual={forward_domain.candidate_count}"
            )
        if len(forward_domain.families) != args.expected_family_count:
            raise RuntimeError(
                "production family-count mismatch: "
                f"expected={args.expected_family_count} actual={len(forward_domain.families)}"
            )

        policy = TargetMultiViewRepairPolicyV2()
        checkpoint_states = _all_valid_rung_states(
            store, reference, forward, selection.policy
        )
        available_checkpoint_sizes = tuple(
            sorted(checkpoint_states.get(args.domain, {}))
        )

        started = time.perf_counter()
        last = started
        previous_proposals = 0
        rung_rows: list[dict[str, Any]] = []
        raw_progress: list[str] = []

        def progress(message: str) -> None:
            nonlocal last, previous_proposals
            raw_progress.append(message)
            fields = _fields(message)
            if fields.get("status") != "rung" or "target_size" not in fields:
                return
            now = time.perf_counter()
            proposals = int(fields.get("proposals", previous_proposals))
            row = {
                "target_size": int(fields["target_size"]),
                "rung_wall_seconds": now - last,
                "cumulative_wall_seconds": now - started,
                "proposals": proposals - previous_proposals,
                "cumulative_proposals": proposals,
                "removal_shortlist_limit": policy.removal_shortlist_limit,
                "swaps": int(fields.get("swaps", 0)),
                "proposal_full_state_copies": int(
                    fields.get("proposal_full_state_copies", -1)
                ),
                "mvstate2_restore_count": int(
                    fields.get("mvstate2_restore_count", 0)
                ),
                "selected_prefix_state_mode": fields.get(
                    "selected_prefix_state_mode", "unknown"
                ),
                "current_rss_kib": _rss_kib(),
                "inverse_mutation": fields.get("inverse_mutation") == "true",
            }
            rung_rows.append(row)
            previous_proposals = proposals
            last = now
            print(message, flush=True)
            print(
                f"qualification_rss_kib={row['current_rss_kib']}; "
                f"rung_wall_seconds={row['rung_wall_seconds']:.6f}",
                flush=True,
            )

        repair = _build_repair_from_checkpoints(
            reference,
            forward,
            selection,
            policy=policy,
            checkpoint_states=checkpoint_states,
            progress_callback=progress,
        )
    finally:
        store.close()

    repair_domain = repair.domain(args.domain)
    observed_sizes = tuple(
        int(rung.target_size) for rung in repair_domain.rungs if rung.materializable
    )
    no_clone = bool(rung_rows) and all(
        row["proposal_full_state_copies"] == 0 for row in rung_rows
    )
    no_inverse_mutation = bool(rung_rows) and all(
        not row["inverse_mutation"] for row in rung_rows
    )
    all_required_rows = tuple(row["target_size"] for row in rung_rows) == expected_sizes

    payload = {
        "schema": "mdstats.benchmark.mvsel2-harden1-v3-repair2-production.v1",
        "source": {"git_head": _git_head()},
        "workplan": {
            "workplan_id": args.workplan_id,
            "plan_revision": args.workplan_revision,
            "workplan_sha256": args.workplan_sha256,
        },
        "input": {
            "campaign_database": str(database),
            "domain": args.domain,
            "mvidx1_content_digest": forward.mvidx1_content_digest,
            "selection_content_digest": selection.content_digest,
            "candidate_count": forward_domain.candidate_count,
            "family_count": len(forward_domain.families),
            "forward_edge_count": int(
                sum(family.edge_count for family in forward_domain.families)
            ),
            "required_materializable_rungs": expected_sizes,
            "observed_repair_rungs": observed_sizes,
            "available_mvstate2_checkpoint_sizes": available_checkpoint_sizes,
        },
        "repair2": {
            "policy": policy.to_dict(),
            "total_wall_seconds": time.perf_counter() - started,
            "total_swaps": repair_domain.total_swaps,
            "rungs": rung_rows,
            "raw_progress": raw_progress,
            "all_required_rungs_measured": all_required_rows,
            "proposal_full_state_copies_zero": no_clone,
            "inverse_arrays_mapped_by_reader": False,
            "inverse_mutation": not no_inverse_mutation,
        },
        "resources": {
            "current_rss_kib": _rss_kib(),
            "process_peak_rss_kib": int(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            ),
            "cpu_workers": 1,
            "gpu_used": False,
            "stage_resource_scope_note": (
                "standalone evidence harness is single-worker; final campaign integration "
                "qualification must separately exercise the StageResourceScope-wrapped path"
            ),
        },
        "qualification": {
            "candidate_and_family_identity_match": True,
            "default_policy_used": True,
            "all_required_rungs_measured": all_required_rows,
            "proposal_full_state_copies_zero": no_clone,
            "inverse_mutation_false": no_inverse_mutation,
            "gpu_status": "DEFERRED_NOT_RUN",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["qualification"], indent=2, sort_keys=True), flush=True)

    passed = all(
        (
            all_required_rows,
            no_clone,
            no_inverse_mutation,
            observed_sizes[: len(expected_sizes)] == expected_sizes,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
