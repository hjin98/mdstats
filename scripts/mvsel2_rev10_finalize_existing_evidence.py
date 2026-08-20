#!/usr/bin/env python3
"""REV10 finalizer: salvage decisive REV9 evidence and benchmark REPAIR2 proposal cost.

This tool deliberately does not rerun MVSEL2. It consumes a completed REV9
evidence capsule, verifies that the material product surface is unchanged,
measures the REPAIR2 ``_proposal`` kernel directly on the authenticated
production forward graph using timing-only synthetic states, and emits the
conservative combined >=10x decision.

Production SQLite is opened read-only and no production record is written.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
from typing import Any

import numpy as np

TARGET_SIZE = 16_384
PROPOSAL_CAP_PER_RUNG = 64 * (32 + 2)
SELECTOR_SAFETY = 1.25
REPAIR_SAFETY = 4.0
SCHEMA = "mdstats.mvsel2-rev10-finalization.v1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _record_ro(connection: sqlite3.Connection, key: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT payload FROM records WHERE key=?", (key,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"missing production record: {key}")
    value = json.loads(str(row[0]))
    if not isinstance(value, dict):
        raise RuntimeError(f"invalid production record: {key}")
    return value


def _git_surface_unchanged(repo: Path, prior: str, paths: list[str]) -> bool:
    if not prior or not paths:
        return False
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{prior}^{{commit}}"],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if exists.returncode != 0:
        return False
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if dirty.returncode != 0 or dirty.stdout.strip():
        return False
    diff = subprocess.run(
        ["git", "diff", "--quiet", prior, "HEAD", "--", *paths],
        cwd=repo,
        check=False,
    )
    return diff.returncode == 0


def _observed_max_rank_seconds(log_text: str) -> float:
    values = [
        float(value)
        for value in re.findall(
            r"observed-max-rank=([0-9]+(?:\.[0-9]+)?)s", log_text
        )
    ]
    if not values:
        raise RuntimeError(
            "evidence log lacks REV9 observed Phase-B rank timing"
        )
    return max(values)


def _proposal_benchmark(
    *,
    database: Path,
    domain_id: str,
    expected_mvidx_digest: str,
    candidates: list[int],
) -> dict[str, Any]:
    from mdstats.training_data.target_coverage_store import (
        read_target_coverage_native_record,
    )
    from mdstats.training_data.target_coverage_sparse_index_store import (
        read_target_coverage_sparse_index_forward_view_native_record,
    )
    from mdstats.training_data.target_multi_view_selector_v2 import (
        TargetMultiViewForwardFamilyStateV2,
        TargetMultiViewForwardStateV2,
        release_target_multi_view_forward_pages_v2,
    )
    from mdstats.training_data import target_multi_view_repair_v2 as repair

    uri = f"file:{database}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    root = database.parent
    try:
        t0 = time.perf_counter()
        reference = read_target_coverage_native_record(
            _record_ro(connection, "target_coverage_reference"), root
        )
        forward = read_target_coverage_sparse_index_forward_view_native_record(
            _record_ro(connection, "target_coverage_sparse_index"), root
        )
        restore_seconds = time.perf_counter() - t0
        if str(forward.mvidx1_content_digest) != str(expected_mvidx_digest):
            raise RuntimeError(
                "production MVIDX digest changed since source evidence"
            )
        reference_domain = reference.domain(domain_id)
        forward_domain = forward.domain(domain_id)
        candidate_count = int(forward_domain.candidate_count)
        policy = repair.TargetMultiViewRepairPolicyV2()

        rows: list[dict[str, Any]] = []
        for removed in candidates:
            removed = int(removed)
            if not 0 <= removed < candidate_count:
                raise RuntimeError(
                    f"benchmark removal candidate out of range: {removed}"
                )

            family_states = []
            for family in forward_domain.families:
                weights = np.asarray(
                    reference_domain.family(family.family_id).weights,
                    dtype=np.float64,
                )
                multiplicity = np.zeros(
                    int(family.witness_count), dtype=np.int32
                )
                witnesses = np.asarray(
                    family.candidate_witness_indices(removed), dtype=np.int64
                )
                if witnesses.size:
                    multiplicity[witnesses] = 2
                coverage_mass = float(
                    np.sum(weights[multiplicity > 0], dtype=np.float64)
                )
                family_states.append(
                    TargetMultiViewForwardFamilyStateV2(
                        family_id=family.family_id,
                        weights=weights,
                        multiplicity=multiplicity,
                        coverage_mass=coverage_mass,
                    )
                )

            obligation_counts = np.asarray(
                [
                    max(0, int(item.minimum_selected_frames))
                    for item in forward_domain.obligations
                ],
                dtype=np.int32,
            )
            unit_counts = np.zeros(
                len(forward_domain.correlation_unit_ids), dtype=np.int32
            )
            unit_counts[
                int(forward_domain.candidate_correlation_unit_codes[removed])
            ] = 1
            available = np.ones(candidate_count, dtype=np.bool_)
            available[removed] = False
            state = TargetMultiViewForwardStateV2(
                available=available,
                selected_order=[removed],
                family_states=family_states,
                obligation_counts=obligation_counts,
                unsatisfied_required_obligation_count=0,
                correlation_unit_counts=unit_counts,
                representative_utility=0.0,
            )
            unique, loss = repair._removal_metrics(
                removed, forward_domain, state
            )
            scratch = repair._RepairProposalScratchV2(forward_domain)

            started = time.perf_counter()
            proposal = repair._proposal(
                reference_domain,
                forward_domain,
                state,
                (0, removed, float(unique), float(loss)),
                policy,
                scratch,
            )
            wall = time.perf_counter() - started
            rows.append(
                {
                    "removed_candidate": removed,
                    "wall_seconds": wall,
                    "proposal_returned": proposal is not None,
                    "removed_unique_coverage": float(unique),
                    "removed_representative_loss": float(loss),
                }
            )
            release_target_multi_view_forward_pages_v2(forward_domain)

        if not rows:
            raise RuntimeError("proposal benchmark produced no measurements")
        return {
            "reference_plus_forward_restore_seconds": restore_seconds,
            "candidate_count": candidate_count,
            "family_count": len(forward_domain.families),
            "rows": rows,
            "max_proposal_wall_seconds": max(
                float(row["wall_seconds"]) for row in rows
            ),
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--production-db", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    evidence = Path(args.evidence).expanduser().resolve()
    database = Path(args.production_db).expanduser().resolve()
    repo = Path.cwd().resolve()
    worker = _load(evidence / "worker.json")
    log_text = (evidence / "worker.log").read_text(
        encoding="utf-8", errors="replace"
    )
    stages = worker.get("stages")
    if not isinstance(stages, dict):
        raise RuntimeError("worker evidence lacks stages")

    for stage_name in ("G5", "LQ1", "LQ2"):
        stage = stages.get(stage_name)
        if not isinstance(stage, dict) or stage.get("status") != "PASS":
            raise RuntimeError(
                f"source evidence {stage_name} is not PASS"
            )

    lq3 = stages.get("LQ3")
    lq4 = stages.get("LQ4")
    if not isinstance(lq3, dict) or not isinstance(lq4, dict):
        raise RuntimeError("source evidence lacks LQ3/LQ4")
    repair_rows = lq3.get("rungs")
    if not isinstance(repair_rows, list) or not repair_rows:
        raise RuntimeError("source LQ3 lacks measured repair rungs")
    if any(int(row.get("proposals", -1)) != 0 for row in repair_rows):
        raise RuntimeError(
            "REV10 salvage is only for zero-proposal production rungs"
        )
    if any(
        int(row.get("proposal_full_state_copies", -1)) != 0
        or bool(row.get("inverse_mutation", True))
        for row in repair_rows
    ):
        raise RuntimeError(
            "source LQ3 no-copy/no-inverse invariant is not clean"
        )
    if lq4.get("reason") != "bounded REPAIR2 proposal cost was not exercised":
        raise RuntimeError(
            "source LQ4 block is not the REV10 salvageable case"
        )

    g5 = stages["G5"]
    material_paths = [
        str(value) for value in g5.get("material_surface_paths", [])
    ]
    prior_head = str(g5.get("candidate_git_head", ""))
    if not _git_surface_unchanged(repo, prior_head, material_paths):
        raise RuntimeError(
            "G5 material product surface changed; source evidence is stale"
        )

    lq1 = stages["LQ1"]
    expected_digest = str(lq1["mvidx1_content_digest"])
    candidate_count = int(lq1["candidate_count"])
    if candidate_count < TARGET_SIZE:
        raise RuntimeError(
            "source evidence cannot materialize frozen 16384 target"
        )

    observed_max = _observed_max_rank_seconds(log_text)
    # Entire source-run elapsed is an upper bound on setup + Phase A + exact
    # rebase + recovery + measured repair work. Charge every target rank at the
    # worst observed current Phase-B rank. This intentionally overcounts work
    # and does not depend on unpersisted per-stage timing.
    prefix_upper = float(worker["elapsed_seconds"])
    selector_upper = SELECTOR_SAFETY * (
        prefix_upper + TARGET_SIZE * observed_max
    )

    shell_unit = max(
        float(row["wall_seconds"]) / max(1, int(row["shell_size"]))
        for row in repair_rows
    )
    total_shell = TARGET_SIZE
    materializable = [
        int(value)
        for value in lq1.get(
            "materializable_rungs_by_authenticated_pool", []
        )
        if int(value) <= TARGET_SIZE
    ]
    if not materializable or materializable[-1] != TARGET_SIZE:
        raise RuntimeError(
            "source materializable ladder does not reach 16384"
        )
    proposal_cap_total = PROPOSAL_CAP_PER_RUNG * len(materializable)

    sample_candidates = [
        int(value) for value in lq1.get("sample_candidates", [])
    ]
    if not sample_candidates:
        sample_candidates = [0, candidate_count // 2, candidate_count - 1]
    proposal_bench = _proposal_benchmark(
        database=database,
        domain_id=args.domain,
        expected_mvidx_digest=expected_digest,
        candidates=sample_candidates,
    )
    max_proposal = float(proposal_bench["max_proposal_wall_seconds"])
    repair_upper = REPAIR_SAFETY * (
        shell_unit * total_shell
        + max_proposal * proposal_cap_total
    )

    baseline = float(lq4["historical_mvsel1_baseline_seconds"])
    combined = baseline / (selector_upper + repair_upper)
    status = "PASS" if combined >= 10.0 else "FAIL"

    payload = {
        "schema": SCHEMA,
        "status": status,
        "source_evidence": str(evidence),
        "source_worker_git_head": worker.get("git_head"),
        "g5_material_surface_reused": True,
        "production": {
            "database": str(database),
            "domain": args.domain,
            "mvidx1_content_digest": expected_digest,
            "production_mutated": False,
        },
        "selector": {
            "method": "conservative_salvage_upper",
            "source_run_elapsed_upper_seconds": prefix_upper,
            "worst_observed_current_phase_b_rank_seconds": observed_max,
            "charged_phase_b_rank_count": TARGET_SIZE,
            "safety_factor": SELECTOR_SAFETY,
            "selector_upper_seconds": selector_upper,
        },
        "repair": {
            "production_zero_proposal_rungs": repair_rows,
            "production_shell_seconds_per_selected_max": shell_unit,
            "total_shell_selected": total_shell,
            "proposal_cap_per_rung": PROPOSAL_CAP_PER_RUNG,
            "proposal_cap_total": proposal_cap_total,
            "proposal_kernel_benchmark": proposal_bench,
            "safety_factor": REPAIR_SAFETY,
            "repair_upper_seconds": repair_upper,
        },
        "performance": {
            "historical_mvsel1_baseline_seconds": baseline,
            "combined_upper_seconds": selector_upper + repair_upper,
            "combined_speedup_lower": combined,
            "minimum_10x_pass": combined >= 10.0,
        },
    }
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else evidence / "rev10-finalization.json"
    )
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"[REV10] selector_upper={selector_upper:.1f}s; "
        f"repair_upper={repair_upper:.1f}s; "
        f"combined_speedup_lower={combined:.3f}x"
    )
    print(
        f"[REV10] FINAL status={status}; "
        f"minimum_10x_pass={combined >= 10.0}"
    )
    print(f"[REV10] evidence={output}")
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
