#!/usr/bin/env python3
"""REV8 lightweight autonomous qualification for production MVSEL2.

The production graph remains full-scale authority, but qualification executes
only bounded production-state probes: native-forward identity, exact 128->256
MVSTATE2 recovery, checkpoint-started REPAIR2 rungs, and a current-candidate
selector projection.  A parent supervisor provides hard containment while the
worker intentionally operates inside a smaller admitted envelope.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from typing import Any, Mapping

import numpy as np

from mvsel2_qualification_support import (
    GIB,
    MIB,
    derive_resource_plan,
    json_dump,
    json_load,
    repair_projection_upper,
    rss_bytes,
    run_supervised_worker,
    selector_projection_upper,
)

DEFAULT_DOMAIN = "label-domain-5aa1ee5d50cd0b23"
DEFAULT_CANDIDATES = 36_408
DEFAULT_FAMILIES = 165
TARGET_SIZE = 16_384
WORKER_SCHEMA = "mdstats.mvsel2-lightweight-qualification.worker.v2"
HISTORICAL_SOURCE_HEAD = "f23426d426af21a54914f4e62181ce09e864330b"
LEGACY_SURFACE = (
    "mdstats/training_data/target_multi_view_selector.py",
    "mdstats/training_data/target_multi_view_selection_state.py",
    "mdstats/training_data/target_multi_view_repair.py",
    "mdstats/training_data/target_coverage_sparse_index.py",
    "benchmarks/mlff_mvsel_production_density_2026-08-18.json",
)


class MaterialQualificationFailure(RuntimeError):
    """A demonstrated candidate/material acceptance failure."""


def _record_ro(connection: sqlite3.Connection, key: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT payload FROM records WHERE key=?", (key,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"missing production campaign record: {key}")
    payload = json.loads(str(row[0]))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid production campaign record: {key}")
    return payload


def _checkpoint_rows_ro(
    connection: sqlite3.Connection, domain: str
) -> dict[int, dict[str, Any]]:
    prefix = f"target_multi_view_selection_state_v2:{domain}:"
    rows = connection.execute(
        "SELECT key,payload FROM records WHERE key LIKE ?", (prefix + "%",)
    ).fetchall()
    result: dict[int, dict[str, Any]] = {}
    for key, encoded in rows:
        try:
            size = int(str(key).rsplit(":", 1)[1])
            payload = json.loads(str(encoded))
        except Exception:
            continue
        if isinstance(payload, dict):
            result[size] = payload
    return result


class _ReadOnlyStore:
    """CampaignStore-shaped adapter backed only by a read-only SQLite handle."""

    def __init__(self, path: Path, connection: sqlite3.Connection) -> None:
        self.path = path
        self._connection = connection

    def _connect(self) -> sqlite3.Connection:
        return self._connection


def _copy_checkpoint_bundle(
    pointer: Mapping[str, Any], production_root: Path, scratch_root: Path
) -> None:
    relative = Path(str(pointer.get("relative_path", "")))
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative in {Path(""), Path(".")}
    ):
        raise RuntimeError("invalid MVSTATE2 pointer path")
    source_manifest = (production_root / relative).resolve()
    if (
        production_root.resolve() not in source_manifest.parents
        or not source_manifest.is_file()
    ):
        raise RuntimeError(
            f"missing production MVSTATE2 manifest: {source_manifest}"
        )
    source_dir = source_manifest.parent
    target_dir = scratch_root / relative.parent
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir, copy_function=shutil.copy2)


def _state_equal(left: Any, right: Any) -> tuple[bool, str]:
    if tuple(left.selected_order) != tuple(right.selected_order):
        return False, "selected_order"
    if not np.array_equal(left.available, right.available):
        return False, "available"
    if len(left.family_states) != len(right.family_states):
        return False, "family_count"
    for index, (a, b) in enumerate(
        zip(left.family_states, right.family_states, strict=True)
    ):
        if a.family_id != b.family_id:
            return False, f"family_id[{index}]"
        if not np.array_equal(a.multiplicity, b.multiplicity):
            return False, f"multiplicity[{index}]"
        if float(a.coverage_mass) != float(b.coverage_mass):
            return False, f"coverage_mass[{index}]"
    if not np.array_equal(left.obligation_counts, right.obligation_counts):
        return False, "obligation_counts"
    if (
        int(left.unsatisfied_required_obligation_count)
        != int(right.unsatisfied_required_obligation_count)
    ):
        return False, "unsatisfied_required_obligation_count"
    if not np.array_equal(
        left.correlation_unit_counts, right.correlation_unit_counts
    ):
        return False, "correlation_unit_counts"
    if float(left.representative_utility) != float(right.representative_utility):
        return False, "representative_utility"
    return True, "exact"


def _legacy_surface_compatible(repo: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            HISTORICAL_SOURCE_HEAD,
            "HEAD",
            "--",
            *LEGACY_SURFACE,
        ],
        cwd=repo,
        check=False,
    )
    if result.returncode == 0:
        return True, "unchanged"
    if result.returncode == 1:
        return False, "legacy MVSEL1 comparator surface changed"
    return False, f"git compatibility check failed: exit={result.returncode}"


def _worker(args: argparse.Namespace) -> int:
    import mdstats
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data import mvsel2_hardening_runtime as hardening
    from mdstats.training_data.mvsel2_repair_checkpoint_runtime import (
        repair_rung_from_authenticated_state,
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
    from mdstats.training_data.target_multi_view_selector_v2 import (
        TargetMultiViewSelectionPlanV2,
        build_target_multi_view_lazy_frontier_v2,
        choose_target_multi_view_phase_a_candidate_v2,
        choose_target_multi_view_phase_b_candidate_v2,
        score_target_multi_view_candidate_v2,
        select_target_multi_view_candidate_v2,
    )

    database = Path(args.production_db).resolve()
    repo = Path(args.repo).resolve()
    scratch = Path(args.worker_scratch).resolve()
    evidence = Path(args.worker_evidence).resolve()
    production_root = database.parent
    operating_rss = int(args.operating_rss_bytes)
    operating_seconds = float(args.operating_seconds)
    worker_started = time.monotonic()

    result: dict[str, Any] = {
        "schema": WORKER_SCHEMA,
        "stages": {},
    }

    def elapsed() -> float:
        return time.monotonic() - worker_started

    uri = f"file:{database}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    store = _ReadOnlyStore(database, connection)
    try:
        # LQ1: bind the complete real authority, but query only tiny incidence.
        stage_started = time.perf_counter()
        reference_pointer = _record_ro(connection, "target_coverage_reference")
        sparse_pointer = _record_ro(connection, "target_coverage_sparse_index")
        reference = read_target_coverage_native_record(
            reference_pointer, production_root
        )
        forward = read_target_coverage_sparse_index_forward_view_native_record(
            sparse_pointer, production_root
        )
        restore_seconds = time.perf_counter() - stage_started
        selection = TargetMultiViewSelectionPlanV2.from_dict(
            _record_ro(connection, "target_multi_view_selection_v2")
        )
        reference_domain = reference.domain(args.domain)
        forward_domain = forward.domain(args.domain)
        selection_domain = selection.domain(args.domain)

        candidate_count = int(forward_domain.candidate_count)
        family_count = len(forward_domain.families)
        edge_count = int(
            sum(family.edge_count for family in forward_domain.families)
        )
        if candidate_count != args.expected_candidates:
            raise RuntimeError(
                "production candidate count mismatch: "
                f"{candidate_count}!={args.expected_candidates}"
            )
        if family_count != args.expected_families:
            raise RuntimeError(
                "production family count mismatch: "
                f"{family_count}!={args.expected_families}"
            )

        materializable = tuple(
            int(rung.target_size)
            for rung in selection_domain.rungs
            if rung.materializable and int(rung.target_size) <= TARGET_SIZE
        )
        if TARGET_SIZE not in materializable:
            raise RuntimeError("production ladder lacks materializable 16384 rung")
        sample_candidates = tuple(
            dict.fromkeys((0, candidate_count // 2, candidate_count - 1))
        )
        sampled_edges = 0
        for candidate in sample_candidates:
            sampled_edges += sum(
                len(family.candidate_witness_indices(candidate))
                for family in forward_domain.families
            )
        result["stages"]["LQ1"] = {
            "status": "PASS",
            "reference_plus_forward_restore_seconds": restore_seconds,
            "candidate_count": candidate_count,
            "family_count": family_count,
            "forward_edge_count": edge_count,
            "mvidx1_content_digest": forward.mvidx1_content_digest,
            "materializable_rungs": materializable,
            "sample_candidates": sample_candidates,
            "sampled_forward_edges": sampled_edges,
            "inverse_arrays_mapped": False,
        }

        checkpoints = _checkpoint_rows_ro(connection, args.domain)
        for required in (128, 256, TARGET_SIZE):
            if required not in checkpoints:
                raise RuntimeError(
                    f"required production MVSTATE2 checkpoint missing: {required}"
                )
        selector_policy = selection.policy

        def restore(size: int) -> Any:
            return hardening._restore_checkpoint(
                checkpoints[size],
                store=store,
                reference_domain=reference_domain,
                forward_domain=forward_domain,
                dataset_id=reference.dataset_id,
                selector_policy=selector_policy,
            )

        state256 = restore(256)
        state16384 = restore(TARGET_SIZE)
        if state16384.selected_count != TARGET_SIZE:
            raise RuntimeError("16384 checkpoint sentinel cardinality mismatch")
        del state16384

        uid_to_candidate = {
            uid: index for index, uid in enumerate(reference_domain.frame_uids)
        }
        canonical_order = [
            uid_to_candidate[entry.frame_uid]
            for entry in selection_domain.master_order
        ]
        rung_by_size = {
            int(rung.target_size): rung for rung in selection_domain.rungs
        }

        # LQ2: corrupt only qualification-owned 256 pointer and prove fallback.
        q2_scratch = scratch / "lq2"
        q2_scratch.mkdir(parents=True, exist_ok=True)
        for size in (128, 256):
            _copy_checkpoint_bundle(
                checkpoints[size], production_root, q2_scratch
            )
        scratch_store = CampaignStore(q2_scratch / "qualification.sqlite3")
        try:
            for size in (128, 256):
                scratch_store.put_record(
                    f"target_multi_view_selection_state_v2:{args.domain}:{size}",
                    checkpoints[size],
                )
            corrupt_key = (
                f"target_multi_view_selection_state_v2:{args.domain}:256"
            )
            db = scratch_store._connect()
            db.execute(
                "UPDATE records SET payload='{}' WHERE key=?", (corrupt_key,)
            )
            db.commit()
            states, pointers = hardening._highest_valid_resume_states(
                scratch_store, reference, forward, selector_policy
            )
            recovered = states.get(args.domain)
            recovered_pointer = pointers.get(args.domain)
            if (
                recovered is None
                or recovered_pointer is None
                or dict(recovered_pointer) != dict(checkpoints[128])
            ):
                raise MaterialQualificationFailure(
                    "runtime recovery did not select the 128 checkpoint"
                )
            for candidate in canonical_order[128:256]:
                score = score_target_multi_view_candidate_v2(
                    candidate, forward_domain, recovered
                )
                select_target_multi_view_candidate_v2(
                    candidate, forward_domain, recovered, score=score
                )
            equal, field = _state_equal(recovered, state256)
            if not equal:
                raise MaterialQualificationFailure(
                    f"128->256 reconstructed state differs at {field}"
                )
        finally:
            scratch_store.close()
            shutil.rmtree(q2_scratch, ignore_errors=True)
        del state256
        result["stages"]["LQ2"] = {
            "status": "PASS",
            "fallback_size": 128,
            "comparison_size": 256,
            "state_equivalence": "exact",
        }

        # LQ3: exact shared repair science, carrying real divergence forward.
        repair_policy = TargetMultiViewRepairPolicyV2()
        repair_rows: list[dict[str, Any]] = []
        repair_state = None
        repair_order = list(canonical_order)
        repair_diverged = False
        for size in (128, 256, 512, 1024):
            optional = size >= 512
            if size not in checkpoints or size not in materializable:
                if optional:
                    continue
                raise RuntimeError(f"mandatory REPAIR2 checkpoint missing: {size}")
            if optional and any(row["proposals"] > 0 for row in repair_rows):
                break
            if optional and elapsed() > 0.40 * operating_seconds:
                break

            shell_start = 0 if size == 128 else max(
                value for value in materializable if value < size
            )
            checkpoint_mode = "mvstate2_authenticated"
            if repair_state is None or not repair_diverged:
                repair_state = restore(size)
                repair_order = list(canonical_order)
            else:
                checkpoint_mode = "post_divergence_carried_state"
                for rank in range(int(repair_state.selected_count), size):
                    candidate = repair_order[rank]
                    score = score_target_multi_view_candidate_v2(
                        candidate, forward_domain, repair_state
                    )
                    select_target_multi_view_candidate_v2(
                        candidate,
                        forward_domain,
                        repair_state,
                        score=score,
                    )

            started = time.perf_counter()
            rung, telemetry = repair_rung_from_authenticated_state(
                reference_domain,
                forward_domain,
                selection,
                rung_by_size[size],
                policy=repair_policy,
                order=repair_order,
                state=repair_state,
                shell_start=shell_start,
            )
            wall = time.perf_counter() - started
            repair_diverged = repair_diverged or bool(rung.swaps)
            repair_rows.append(
                {
                    "target_size": size,
                    "shell_size": size - shell_start,
                    "wall_seconds": wall,
                    "proposals": int(telemetry["proposals"]),
                    "swaps": len(rung.swaps),
                    "proposal_full_state_copies": int(
                        telemetry["proposal_full_state_copies"]
                    ),
                    "inverse_mutation": bool(telemetry["inverse_mutation"]),
                    "checkpoint_mode": checkpoint_mode,
                    "current_rss_bytes": rss_bytes(os.getpid()),
                }
            )

        if tuple(row["target_size"] for row in repair_rows[:2]) != (128, 256):
            raise RuntimeError("mandatory 128/256 REPAIR2 measurements absent")
        if any(
            row["proposal_full_state_copies"] != 0
            or row["inverse_mutation"]
            for row in repair_rows
        ):
            raise MaterialQualificationFailure(
                "REPAIR2 no-copy/no-inverse invariant failed"
            )

        repair_upper = repair_projection_upper(
            repair_rows,
            candidate_count=candidate_count,
            materializable_sizes=materializable,
            removal_shortlist_limit=repair_policy.removal_shortlist_limit,
            max_swaps_per_shell=repair_policy.max_swaps_per_shell,
            max_passes_per_shell=repair_policy.max_passes_per_shell,
        )
        result["stages"]["LQ3"] = {
            "status": "PASS" if repair_upper is not None else "BLOCKED",
            "rungs": repair_rows,
            "large_checkpoint_sentinel": TARGET_SIZE,
            "repair_upper_seconds": repair_upper,
        }

        # LQ4: reuse only legacy MVSEL1 baseline; measure current MVSEL2 hot path.
        historical_v1 = json_load(
            repo / "benchmarks/mlff_mvsel_production_density_2026-08-18.json"
        )
        historical_preflight = json_load(
            repo / "benchmarks/mlff_mvsel2_phase_a_preflight_2026-08-18.json"
        )
        historical_density = json_load(
            repo / "benchmarks/mlff_mvsel2_production_density_2026-08-18.json"
        )
        legacy_input = historical_v1["input"]
        baseline_ok = True
        baseline_reason = "compatible"
        if (
            int(legacy_input["candidate_count"]) != candidate_count
            or int(legacy_input["family_count"]) != family_count
            or int(legacy_input["edge_count"]) != edge_count
            or str(legacy_input["dataset_digest"])
            != str(forward.mvidx1_content_digest)
        ):
            baseline_ok = False
            baseline_reason = "legacy baseline production graph mismatch"
        elif (
            platform.node() != "local-user-ProBuild"
            and not args.accept_same_host_equivalent
        ):
            baseline_ok = False
            baseline_reason = f"legacy baseline host mismatch: {platform.node()}"
        else:
            baseline_ok, baseline_reason = _legacy_surface_compatible(repo)

        baseline_full = float(
            historical_v1["optimized"]["initialization_seconds"]
        ) + TARGET_SIZE * float(
            historical_v1["optimized"]["rank_0_update_seconds"]
        )

        if not baseline_ok:
            result["stages"]["LQ4"] = {
                "status": "BLOCKED",
                "reason": baseline_reason,
                "historical_mvsel1_baseline_seconds": baseline_full,
            }
        elif repair_upper is None:
            result["stages"]["LQ4"] = {
                "status": "BLOCKED",
                "reason": "bounded REPAIR2 proposal cost was not exercised",
                "historical_mvsel1_baseline_seconds": baseline_full,
            }
        else:
            state = restore(128)
            phase_a_rows: list[dict[str, Any]] = []
            phase_a_started = time.perf_counter()
            while (
                state.unsatisfied_required_obligation_count > 0
                or any(
                    family.coverage_mass
                    < selector_policy.coverage_threshold
                    - selector_policy.gain_tie_tolerance
                    for family in state.family_states
                )
            ):
                rank = state.selected_count
                rank_started = time.perf_counter()
                choice = choose_target_multi_view_phase_a_candidate_v2(
                    reference_domain, forward_domain, state
                )
                if choice.candidate_index != canonical_order[rank]:
                    raise MaterialQualificationFailure(
                        f"current Phase-A candidate mismatch at rank {rank}"
                    )
                select_target_multi_view_candidate_v2(
                    choice.candidate_index,
                    forward_domain,
                    state,
                    score=choice.score,
                )
                phase_a_rows.append(
                    {
                        "rank": rank,
                        "seconds": time.perf_counter() - rank_started,
                    }
                )
            phase_a_seconds = time.perf_counter() - phase_a_started
            phase_a_end = state.selected_count
            if not phase_a_rows:
                raise RuntimeError(
                    "current production authority completes Phase A before rank 128"
                )
            max_phase_a = max(
                float(row["seconds"]) for row in phase_a_rows
            )

            # The REV8 frontier is family-streaming.  Admission is therefore
            # based on current resident state plus one largest family mmap,
            # rather than historical post-release RSS or the entire 35+ GiB
            # forward mapping.  The external supervisor remains the hard guard.
            largest_family_bytes = max(
                int(np.asarray(family.candidate_offsets).nbytes)
                + int(np.asarray(family.candidate_witnesses).nbytes)
                for family in forward_domain.families
            )
            current_rss = int(rss_bytes(os.getpid()) or 0)
            admitted_rebase_rss = (
                current_rss
                + 2 * largest_family_bytes
                + 2 * GIB
            )
            historical_rebase_seconds = float(
                historical_density["phase_b"]["exact_rebase_seconds"]
            )
            admitted_rebase_time = 1.5 * historical_rebase_seconds + 90.0
            if admitted_rebase_rss > operating_rss:
                result["stages"]["LQ4"] = {
                    "status": "BLOCKED",
                    "reason": "current operating envelope does not admit exact streaming Phase-B rebase",
                    "projected_rebase_rss_bytes": admitted_rebase_rss,
                    "largest_family_mapped_bytes": largest_family_bytes,
                    "operating_rss_bytes": operating_rss,
                }
            elif elapsed() + admitted_rebase_time > operating_seconds:
                result["stages"]["LQ4"] = {
                    "status": "BLOCKED",
                    "reason": "current operating time envelope does not admit exact Phase-B rebase",
                    "elapsed_seconds": elapsed(),
                    "operating_seconds": operating_seconds,
                }
            else:
                rebase_started = time.perf_counter()
                frontier = build_target_multi_view_lazy_frontier_v2(
                    forward_domain, state
                )
                rebase_seconds = time.perf_counter() - rebase_started
                phase_b_rows: list[dict[str, Any]] = []
                for _ in range(min(32, TARGET_SIZE - state.selected_count)):
                    rank = state.selected_count
                    rank_started = time.perf_counter()
                    choice = choose_target_multi_view_phase_b_candidate_v2(
                        reference_domain, forward_domain, state, frontier
                    )
                    if choice.candidate_index != canonical_order[rank]:
                        raise MaterialQualificationFailure(
                            f"current Phase-B candidate mismatch at rank {rank}"
                        )
                    select_target_multi_view_candidate_v2(
                        choice.candidate_index,
                        forward_domain,
                        state,
                        score=choice.score,
                    )
                    phase_b_rows.append(
                        {
                            "rank": rank,
                            "seconds": time.perf_counter() - rank_started,
                            "fallback": bool(choice.telemetry.fallback_used),
                        }
                    )
                if not phase_b_rows:
                    raise RuntimeError("no Phase-B ranks available for projection")
                max_phase_b = max(
                    float(row["seconds"]) for row in phase_b_rows
                )
                selector_upper = selector_projection_upper(
                    current_restore_seconds=restore_seconds,
                    historical_cold_preflight_seconds=float(
                        historical_preflight["cold_preflight"]["total_seconds"]
                    ),
                    phase_a_prefix_size=128,
                    max_phase_a_rank_seconds=max_phase_a,
                    measured_phase_a_seconds=phase_a_seconds,
                    exact_rebase_seconds=rebase_seconds,
                    phase_a_end=phase_a_end,
                    max_phase_b_rank_seconds=max_phase_b,
                    target_size=TARGET_SIZE,
                )
                combined = baseline_full / (
                    selector_upper + float(repair_upper)
                )
                result["stages"]["LQ4"] = {
                    "status": "PASS" if combined >= 10.0 else "FAIL",
                    "historical_mvsel1_baseline_seconds": baseline_full,
                    "legacy_surface_compatible": True,
                    "phase_a_start": 128,
                    "phase_a_end": phase_a_end,
                    "phase_a_measured_seconds": phase_a_seconds,
                    "phase_a_max_rank_seconds": max_phase_a,
                    "exact_rebase_seconds": rebase_seconds,
                    "phase_b_sampled_ranks": len(phase_b_rows),
                    "phase_b_max_rank_seconds": max_phase_b,
                    "phase_b_fallback_count": sum(
                        bool(row["fallback"]) for row in phase_b_rows
                    ),
                    "selector_upper_seconds": selector_upper,
                    "repair_upper_seconds": repair_upper,
                    "combined_speedup_lower": combined,
                    "minimum_10x_pass": combined >= 10.0,
                    "historical_mvsel2_projection_advisory": float(
                        historical_density["projection"]["projected_speedup"]
                    ),
                }

        statuses = [
            str(stage.get("status", "BLOCKED"))
            for stage in result["stages"].values()
        ]
        if "FAIL" in statuses:
            overall = "FAIL"
        elif "BLOCKED" in statuses:
            overall = "BLOCKED"
        else:
            overall = "PASS"
        result.update(
            status=overall,
            git_head=subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            elapsed_seconds=elapsed(),
            production={
                "database": str(database),
                "domain": args.domain,
                "mvidx1_content_digest": forward.mvidx1_content_digest,
            },
        )
        json_dump(evidence / "worker.json", result)
        return 0 if overall == "PASS" else (2 if overall == "FAIL" else 3)
    except MaterialQualificationFailure as exc:
        result.update(
            status="FAIL",
            failure_class="PRODUCT_FAILURE",
            error=f"{type(exc).__name__}: {exc}",
            elapsed_seconds=elapsed(),
        )
        json_dump(evidence / "worker.json", result)
        return 2
    except Exception as exc:
        result.update(
            status="BLOCKED",
            failure_class="HARNESS_OR_INPUT_BLOCKED",
            error=f"{type(exc).__name__}: {exc}",
            elapsed_seconds=elapsed(),
        )
        json_dump(evidence / "worker.json", result)
        return 3
    finally:
        connection.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-db")
    parser.add_argument("--config")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--root", default="qualification/bounded-mvsel2")
    parser.add_argument("--expected-candidates", type=int, default=DEFAULT_CANDIDATES)
    parser.add_argument("--expected-families", type=int, default=DEFAULT_FAMILIES)
    parser.add_argument("--max-rss-gib", type=float)
    parser.add_argument("--max-scratch-gib", type=float)
    parser.add_argument("--total-timeout-seconds", type=float)
    parser.add_argument("--accept-same-host-equivalent", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--repo", help=argparse.SUPPRESS)
    parser.add_argument("--worker-scratch", help=argparse.SUPPRESS)
    parser.add_argument("--worker-evidence", help=argparse.SUPPRESS)
    parser.add_argument("--operating-rss-bytes", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--operating-seconds", type=float, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.production_db:
        raise SystemExit("--production-db is required")
    database = Path(args.production_db).expanduser().resolve()
    config = Path(args.config).expanduser().resolve() if args.config else None
    if args.worker:
        required = (
            "repo",
            "worker_scratch",
            "worker_evidence",
            "operating_rss_bytes",
            "operating_seconds",
        )
        for name in required:
            if getattr(args, name) is None:
                raise SystemExit(
                    f"--{name.replace('_', '-')} is required in worker mode"
                )
        return _worker(args)

    if not database.is_file():
        raise RuntimeError(f"production database not found: {database}")
    if config is not None and not config.is_file():
        raise RuntimeError(f"campaign config not found: {config}")

    repo = Path.cwd().resolve()
    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if root == database.parent or database.parent in root.parents:
        raise RuntimeError("qualification root must be outside production .mdstats")

    plan = derive_resource_plan(
        root=root,
        max_rss_gib=args.max_rss_gib,
        max_scratch_gib=args.max_scratch_gib,
        total_seconds=args.total_timeout_seconds,
    )
    if plan.hard_scratch_bytes < 128 * MIB:
        raise RuntimeError("safe scratch containment is below minimum requirement")
    if plan.free_disk_bytes < plan.hard_scratch_bytes + 2 * GIB:
        raise RuntimeError("insufficient free-disk headroom for qualification")

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--production-db",
        str(database),
        "--domain",
        args.domain,
        "--repo",
        str(repo),
        "--expected-candidates",
        str(args.expected_candidates),
        "--expected-families",
        str(args.expected_families),
    ]
    if config is not None:
        command += ["--config", str(config)]
    if args.accept_same_host_equivalent:
        command.append("--accept-same-host-equivalent")

    print(
        "[REV8 qualification] "
        f"cpu={plan.cpu_count}; "
        f"effective-memory={plan.effective_available_bytes / GIB:.1f} GiB; "
        f"operating-rss={plan.operating_rss_bytes / GIB:.1f} GiB; "
        f"hard-rss={plan.hard_rss_bytes / GIB:.1f} GiB; "
        f"operating-wall={plan.operating_total_seconds:.0f}s; "
        f"hard-wall={plan.hard_total_seconds:.0f}s; "
        f"hard-scratch={plan.hard_scratch_bytes / GIB:.2f} GiB",
        flush=True,
    )
    return run_supervised_worker(
        command=command,
        repo=repo,
        database=database,
        config=config,
        root=root,
        plan=plan,
    )


if __name__ == "__main__":
    raise SystemExit(main())
