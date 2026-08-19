#!/usr/bin/env python3
"""REV9 worker adaptation for campaigns with no pre-existing MVSEL2/MVSTATE2.

The production reference and native-forward MVIDX remain the scientific input
authority.  Qualification generates only the bounded current selector prefix it
already needs for performance measurement, persists qualification-owned 128/256
MVSTATE2 checkpoints, and uses those checkpoints to exercise exact recovery and
checkpoint-started REPAIR2.  No production record is written.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import time
from types import SimpleNamespace
from typing import Any

import numpy as np


def _empty_bound_state(reference_domain: Any, forward_domain: Any) -> Any:
    """Allocate the exact post-validation mutable state without a full graph scan."""
    from mdstats.training_data.target_multi_view_selector_v2 import (
        TargetMultiViewForwardFamilyStateV2,
        TargetMultiViewForwardStateV2,
    )

    candidate_count = int(forward_domain.candidate_count)
    if len(reference_domain.frame_uids) != candidate_count:
        raise RuntimeError("reference/candidate cardinality mismatch")
    family_states = []
    for family in forward_domain.families:
        weights = np.asarray(
            reference_domain.family(family.family_id).weights, dtype=np.float64
        )
        if weights.shape != (int(family.witness_count),):
            raise RuntimeError(
                f"reference/forward witness cardinality mismatch: {family.family_id}"
            )
        if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
            raise RuntimeError(f"invalid reference weights: {family.family_id}")
        family_states.append(
            TargetMultiViewForwardFamilyStateV2(
                family_id=family.family_id,
                weights=weights,
                multiplicity=np.zeros(int(family.witness_count), dtype=np.int32),
            )
        )
    required = np.asarray(
        [bool(item.required) for item in forward_domain.obligations], dtype=np.bool_
    )
    unit_codes = np.asarray(
        forward_domain.candidate_correlation_unit_codes, dtype=np.int64
    )
    if unit_codes.shape != (candidate_count,):
        raise RuntimeError("candidate correlation-unit cardinality mismatch")
    if unit_codes.size and (
        int(np.min(unit_codes)) < 0
        or int(np.max(unit_codes)) >= len(forward_domain.correlation_unit_ids)
    ):
        raise RuntimeError("candidate correlation-unit code is out of range")
    return TargetMultiViewForwardStateV2(
        available=np.ones(candidate_count, dtype=np.bool_),
        selected_order=[],
        family_states=family_states,
        obligation_counts=np.zeros(len(forward_domain.obligations), dtype=np.int32),
        unsatisfied_required_obligation_count=int(np.count_nonzero(required)),
        correlation_unit_counts=np.zeros(
            len(forward_domain.correlation_unit_ids), dtype=np.int32
        ),
        representative_utility=0.0,
    )


def _phase_a_pending(state: Any, policy: Any) -> bool:
    return bool(
        state.unsatisfied_required_obligation_count > 0
        or any(
            family.coverage_mass
            < policy.coverage_threshold - policy.gain_tie_tolerance
            for family in state.family_states
        )
    )


def _base_rung(reference_domain: Any, forward_domain: Any, state: Any, policy: Any) -> Any:
    from mdstats.training_data.target_multi_view_selector import (
        TargetMultiViewSelectionRung,
    )

    order = tuple(int(value) for value in state.selected_order)
    coverage = tuple(
        sorted(
            (
                str(item.family_id),
                min(1.0, max(0.0, float(item.coverage_mass))),
            )
            for item in state.family_states
        )
    )
    unsatisfied = tuple(
        sorted(
            str(item.obligation_id)
            for index, item in enumerate(forward_domain.obligations)
            if item.required
            and int(state.obligation_counts[index]) < int(item.minimum_selected_frames)
        )
    )
    qualified = not unsatisfied and all(
        value >= policy.coverage_threshold - policy.gain_tie_tolerance
        for _family_id, value in coverage
    )
    return TargetMultiViewSelectionRung(
        target_size=len(order),
        materializable=True,
        frame_uids=tuple(reference_domain.frame_uids[candidate] for candidate in order),
        family_coverage=coverage,
        hard_obligations_passed=not unsatisfied,
        unsatisfied_obligation_ids=unsatisfied,
        hard_coverage_qualified=qualified,
        phase_at_boundary="representative_fill" if qualified else "hard_coverage",
        shell_coverage_gain=0.0,
        shell_representative_gain=0.0,
    )


def _state_digest(state: Any, reference_domain: Any) -> str:
    from mdstats.training_data._common import digest

    return digest(
        tuple(reference_domain.frame_uids[int(candidate)] for candidate in state.selected_order)
    )


def install(engine: Any) -> None:
    """Install the no-preexisting-artifact worker into the frozen supervisor."""
    engine._worker = lambda args: _worker(engine, args)


def _worker(engine: Any, args: Any) -> int:
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
    from mdstats.training_data.target_multi_view_selection_state_v2 import (
        build_target_multi_view_selection_identity_v2,
        checkpoint_target_multi_view_forward_state_v2,
        write_target_multi_view_selection_checkpoint_v2,
    )
    from mdstats.training_data.target_multi_view_selector_v2 import (
        TargetMultiViewSelectorPolicyV2,
        build_target_multi_view_lazy_frontier_v2,
        choose_target_multi_view_phase_a_candidate_v2,
        choose_target_multi_view_phase_b_candidate_v2,
        release_target_multi_view_forward_pages_v2,
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
        "schema": "mdstats.mvsel2-lightweight-qualification.worker.v3",
        "qualification_revision": 9,
        "selection_authority_source": (
            "CURRENT_CANDIDATE_FROZEN_POLICY_ON_AUTHENTICATED_PRODUCTION_GRAPH"
        ),
        "preexisting_final_plan_required": False,
        "preexisting_mvstate2_required": False,
        "stages": {},
    }

    def elapsed() -> float:
        return time.monotonic() - worker_started

    uri = f"file:{database}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    scratch_store = None
    try:
        try:
            result["stages"]["G5"] = engine.run_preflight(repo, scratch, evidence)
        except engine.PreflightProductFailure as exc:
            raise engine.MaterialQualificationFailure(str(exc)) from exc

        # LQ1: authenticate immutable production inputs.  A completed selector
        # product is deliberately not required because this campaign predates
        # MVSEL2 persistence.
        stage_started = time.perf_counter()
        reference_pointer = engine._record_ro(connection, "target_coverage_reference")
        sparse_pointer = engine._record_ro(connection, "target_coverage_sparse_index")
        reference = read_target_coverage_native_record(reference_pointer, production_root)
        forward = read_target_coverage_sparse_index_forward_view_native_record(
            sparse_pointer, production_root
        )
        restore_seconds = time.perf_counter() - stage_started
        reference_domain = reference.domain(args.domain)
        forward_domain = forward.domain(args.domain)
        policy = TargetMultiViewSelectorPolicyV2()

        candidate_count = int(forward_domain.candidate_count)
        family_count = len(forward_domain.families)
        edge_count = int(sum(family.edge_count for family in forward_domain.families))
        if candidate_count != args.expected_candidates:
            raise RuntimeError(
                f"production candidate count mismatch: {candidate_count}!="
                f"{args.expected_candidates}"
            )
        if family_count != args.expected_families:
            raise RuntimeError(
                f"production family count mismatch: {family_count}!={args.expected_families}"
            )
        reference_family_ids = tuple(
            sorted(str(item.family_id) for item in reference_domain.families)
        )
        forward_family_ids = tuple(str(item.family_id) for item in forward_domain.families)
        if reference_family_ids != forward_family_ids:
            raise RuntimeError("reference/forward canonical family identity mismatch")

        materializable = tuple(
            int(size) for size in policy.target_sizes if int(size) <= candidate_count
        )
        if engine.TARGET_SIZE not in materializable:
            raise RuntimeError("authenticated candidate pool cannot materialize 16384")
        selection_identity = build_target_multi_view_selection_identity_v2(
            reference_domain,
            forward_domain,
            dataset_id=reference.dataset_id,
            selector_policy=policy.to_dict(),
        )
        final_plan_present = connection.execute(
            "SELECT 1 FROM records WHERE key=?",
            ("target_multi_view_selection_v2",),
        ).fetchone() is not None
        checkpoint_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM records WHERE key LIKE ?",
                (f"target_multi_view_selection_state_v2:{args.domain}:%",),
            ).fetchone()[0]
        )
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
            "selection_identity_digest": selection_identity.content_digest,
            "frozen_target_sizes": policy.target_sizes,
            "materializable_rungs_by_authenticated_pool": materializable,
            "target_16384_capability_admitted": True,
            "materializable_basis": (
                "frozen_policy_target_sizes_and_authenticated_candidate_count"
            ),
            "preexisting_final_plan_present": final_plan_present,
            "preexisting_mvstate2_pointer_count": checkpoint_count,
            "sample_candidates": sample_candidates,
            "sampled_forward_edges": sampled_edges,
            "inverse_arrays_mapped": False,
            "full_forward_feasibility_scan_performed": False,
        }

        # One exact current selector run supplies all bounded production-state
        # evidence.  Allocate the same state as the production builder after its
        # full feasibility validator, which is intentionally not rerun here.
        state = _empty_bound_state(reference_domain, forward_domain)
        qroot = scratch / "generated-mvstate2"
        qroot.mkdir(parents=True, exist_ok=True)
        scratch_store = CampaignStore(qroot / "qualification.sqlite3")
        checkpoint_pointers: dict[int, dict[str, Any]] = {}
        canonical_order: list[int] = []
        phase_a_rows: list[dict[str, Any]] = []

        def persist_current(size: int) -> dict[str, Any]:
            if int(state.selected_count) != int(size):
                raise RuntimeError(
                    f"checkpoint request {size} != state {state.selected_count}"
                )
            frozen = checkpoint_target_multi_view_forward_state_v2(
                state, selection_identity
            )
            pointer = write_target_multi_view_selection_checkpoint_v2(
                frozen, scratch_store.external_record_directory
            )
            checkpoint_pointers[int(size)] = dict(pointer)
            scratch_store.put_record(
                f"target_multi_view_selection_state_v2:{args.domain}:{size}",
                pointer,
            )
            return dict(pointer)

        while _phase_a_pending(state, policy):
            rank = int(state.selected_count)
            rank_started = time.perf_counter()
            choice = choose_target_multi_view_phase_a_candidate_v2(
                reference_domain, forward_domain, state
            )
            select_target_multi_view_candidate_v2(
                choice.candidate_index, forward_domain, state, score=choice.score
            )
            rank_seconds = time.perf_counter() - rank_started
            canonical_order.append(int(choice.candidate_index))
            phase_a_rows.append(
                {
                    "rank": rank,
                    "seconds": rank_seconds,
                    "candidate_index": int(choice.candidate_index),
                }
            )
            if state.selected_count in (128, 256):
                persist_current(int(state.selected_count))
            if state.selected_count > engine.TARGET_SIZE:
                raise RuntimeError("Phase A exceeded frozen 16384 target")

        phase_a_end = int(state.selected_count)
        if phase_a_end <= 256:
            raise RuntimeError(
                "production Phase A completed before required 256-state evidence"
            )
        if 128 not in checkpoint_pointers or 256 not in checkpoint_pointers:
            raise RuntimeError("qualification-owned 128/256 MVSTATE2 was not captured")
        phase_a_seconds = float(sum(float(row["seconds"]) for row in phase_a_rows))
        max_phase_a = max(float(row["seconds"]) for row in phase_a_rows)
        phase_a_prefix_digest = _state_digest(state, reference_domain)

        # LQ2: the exact runtime recovery mechanism is exercised with
        # qualification-owned checkpoints generated from the real production
        # graph.  Production remains read-only.
        pointer128 = checkpoint_pointers[128]
        pointer256 = checkpoint_pointers[256]
        corrupt_key = f"target_multi_view_selection_state_v2:{args.domain}:256"
        db = scratch_store._connect()
        db.execute("UPDATE records SET payload='{}' WHERE key=?", (corrupt_key,))
        db.commit()
        states, pointers = hardening._highest_valid_resume_states(
            scratch_store, reference, forward, policy
        )
        recovered = states.get(args.domain)
        recovered_pointer = pointers.get(args.domain)
        if (
            recovered is None
            or recovered_pointer is None
            or dict(recovered_pointer) != dict(pointer128)
        ):
            raise engine.MaterialQualificationFailure(
                "runtime recovery did not fall back to qualification-owned rank 128"
            )
        target256 = hardening._restore_checkpoint(
            pointer256,
            store=scratch_store,
            reference_domain=reference_domain,
            forward_domain=forward_domain,
            dataset_id=reference.dataset_id,
            selector_policy=policy,
        )
        for candidate in canonical_order[128:256]:
            score = score_target_multi_view_candidate_v2(
                candidate, forward_domain, recovered
            )
            select_target_multi_view_candidate_v2(
                candidate, forward_domain, recovered, score=score
            )
        equal, field = engine._state_equal(recovered, target256)
        if not equal:
            raise engine.MaterialQualificationFailure(
                f"qualification-owned 128->256 recovery differs at {field}"
            )
        result["stages"]["LQ2"] = {
            "status": "PASS",
            "authority": "qualification_owned_states_on_authenticated_production_graph",
            "fallback_size": 128,
            "comparison_size": 256,
            "state_equivalence": "exact",
            "production_mutated": False,
            "production_checkpoint_claim": False,
        }
        del recovered, target256

        # LQ3 mandatory 128/256 REPAIR2 measurements.  Accepted-swap future-rank
        # inheritance remains fixture authority unless the generated selector
        # prefix contains the displaced future rank; proposal/no-copy/no-inverse
        # and same-N non-regression are measured on the real graph.
        repair_policy = TargetMultiViewRepairPolicyV2()
        selection_stub = SimpleNamespace(policy=policy)
        repair_rows: list[dict[str, Any]] = []

        def measure_repair(size: int, shell_start: int) -> None:
            pointer = checkpoint_pointers[size]
            repair_state = hardening._restore_checkpoint(
                pointer,
                store=scratch_store,
                reference_domain=reference_domain,
                forward_domain=forward_domain,
                dataset_id=reference.dataset_id,
                selector_policy=policy,
            )
            base_rung = _base_rung(
                reference_domain, forward_domain, repair_state, policy
            )
            order = list(canonical_order)
            if len(order) < size:
                raise RuntimeError(f"selector prefix shorter than repair rung {size}")
            started = time.perf_counter()
            rung, telemetry = repair_rung_from_authenticated_state(
                reference_domain,
                forward_domain,
                selection_stub,
                base_rung,
                policy=repair_policy,
                order=order,
                state=repair_state,
                shell_start=shell_start,
            )
            wall = time.perf_counter() - started
            unresolved_future_swap = any(
                swap.displaced_future_rank is None for swap in rung.swaps
            )
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
                    "checkpoint_mode": "qualification_owned_authenticated_mvstate2",
                    "accepted_swap_future_rank_fully_observed": (
                        not unresolved_future_swap
                    ),
                    "accepted_swap_trace_authority": (
                        "current_production_prefix"
                        if rung.swaps and not unresolved_future_swap
                        else "focused_fixture"
                        if rung.swaps
                        else "not_exercised"
                    ),
                    "current_rss_bytes": engine.rss_bytes(os.getpid()),
                }
            )

        measure_repair(128, 0)
        measure_repair(256, 128)
        if any(
            row["proposal_full_state_copies"] != 0 or row["inverse_mutation"]
            for row in repair_rows
        ):
            raise engine.MaterialQualificationFailure(
                "REPAIR2 no-copy/no-inverse invariant failed"
            )

        # LQ4 uses the same live Phase-A state.  Release scanned file pages before
        # admission and build the exact shared streaming Phase-B frontier once.
        historical_v1 = engine.json_load(
            repo / "benchmarks/mlff_mvsel_production_density_2026-08-18.json"
        )
        historical_preflight = engine.json_load(
            repo / "benchmarks/mlff_mvsel2_phase_a_preflight_2026-08-18.json"
        )
        historical_density = engine.json_load(
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
            baseline_ok, baseline_reason = engine._legacy_surface_compatible(repo)
        baseline_full = float(
            historical_v1["optimized"]["initialization_seconds"]
        ) + engine.TARGET_SIZE * float(
            historical_v1["optimized"]["rank_0_update_seconds"]
        )

        release_target_multi_view_forward_pages_v2(forward_domain)
        largest_family_bytes = max(
            int(np.asarray(family.candidate_offsets).nbytes)
            + int(np.asarray(family.candidate_witnesses).nbytes)
            for family in forward_domain.families
        )
        current_rss = int(engine.rss_bytes(os.getpid()) or 0)
        admitted_rebase_rss = current_rss + 2 * largest_family_bytes + 2 * engine.GIB
        historical_rebase_seconds = float(
            historical_density["phase_b"]["exact_rebase_seconds"]
        )
        admitted_rebase_time = 1.5 * historical_rebase_seconds + 90.0

        rebase_block_reason = None
        frontier = None
        rebase_seconds = None
        phase_b_rows: list[dict[str, Any]] = []
        optional_phase_b_rows: list[dict[str, Any]] = []
        if admitted_rebase_rss > operating_rss:
            rebase_block_reason = (
                "current operating envelope does not admit exact streaming Phase-B rebase"
            )
        elif elapsed() + admitted_rebase_time > operating_seconds:
            rebase_block_reason = (
                "current operating time envelope does not admit exact Phase-B rebase"
            )
        else:
            rebase_started = time.perf_counter()
            frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, state)
            rebase_seconds = time.perf_counter() - rebase_started
            for _ in range(min(32, engine.TARGET_SIZE - state.selected_count)):
                rank = int(state.selected_count)
                rank_started = time.perf_counter()
                choice = choose_target_multi_view_phase_b_candidate_v2(
                    reference_domain, forward_domain, state, frontier
                )
                select_target_multi_view_candidate_v2(
                    choice.candidate_index,
                    forward_domain,
                    state,
                    score=choice.score,
                )
                canonical_order.append(int(choice.candidate_index))
                phase_b_rows.append(
                    {
                        "rank": rank,
                        "seconds": time.perf_counter() - rank_started,
                        "candidate_index": int(choice.candidate_index),
                        "fallback": bool(choice.telemetry.fallback_used),
                    }
                )

        phase_b_sample_digest = (
            _state_digest(state, reference_domain) if phase_b_rows else None
        )

        # If mandatory repair rungs produced no proposals, add the smallest
        # additional current selector rung only when already admitted work can
        # reach it safely.  Stop as soon as proposal cost is measured.
        if frontier is not None and not any(
            int(row["proposals"]) > 0 for row in repair_rows
        ):
            for optional_size in (512, 1024):
                if optional_size > engine.TARGET_SIZE:
                    break
                if state.selected_count < optional_size:
                    sampled_max = max(
                        [float(row["seconds"]) for row in phase_b_rows]
                        + [float(row["seconds"]) for row in optional_phase_b_rows]
                        + [1.0]
                    )
                    remaining = optional_size - int(state.selected_count)
                    if elapsed() + 1.5 * remaining * sampled_max > operating_seconds:
                        break
                    while state.selected_count < optional_size:
                        rank = int(state.selected_count)
                        rank_started = time.perf_counter()
                        choice = choose_target_multi_view_phase_b_candidate_v2(
                            reference_domain, forward_domain, state, frontier
                        )
                        select_target_multi_view_candidate_v2(
                            choice.candidate_index,
                            forward_domain,
                            state,
                            score=choice.score,
                        )
                        canonical_order.append(int(choice.candidate_index))
                        optional_phase_b_rows.append(
                            {
                                "rank": rank,
                                "seconds": time.perf_counter() - rank_started,
                                "candidate_index": int(choice.candidate_index),
                                "fallback": bool(choice.telemetry.fallback_used),
                            }
                        )
                if state.selected_count == optional_size:
                    persist_current(optional_size)
                    previous = 256 if optional_size == 512 else 512
                    measure_repair(optional_size, previous)
                if any(int(row["proposals"]) > 0 for row in repair_rows):
                    break

        repair_upper = engine.repair_projection_upper(
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
            "repair_upper_seconds": repair_upper,
            "large_rung_capability_basis": {
                "target_size": engine.TARGET_SIZE,
                "policy_contains_target": engine.TARGET_SIZE in policy.target_sizes,
                "authenticated_candidate_count_sufficient": (
                    candidate_count >= engine.TARGET_SIZE
                ),
                "current_phase_b_transition_executed": frontier is not None,
                "performance_projection_extends_to_target": repair_upper is not None,
                "preexisting_16384_checkpoint_required": False,
                "historical_16384_execution": "advisory_only",
            },
        }

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
        elif rebase_block_reason is not None or frontier is None or rebase_seconds is None:
            result["stages"]["LQ4"] = {
                "status": "BLOCKED",
                "reason": rebase_block_reason or "Phase-B rebase unavailable",
                "projected_rebase_rss_bytes": admitted_rebase_rss,
                "largest_family_mapped_bytes": largest_family_bytes,
                "operating_rss_bytes": operating_rss,
            }
        elif not phase_b_rows:
            result["stages"]["LQ4"] = {
                "status": "BLOCKED",
                "reason": "no Phase-B ranks available for projection",
            }
        else:
            projection_phase_b_rows = phase_b_rows + optional_phase_b_rows
            max_phase_b = max(
                float(row["seconds"]) for row in projection_phase_b_rows
            )
            selector_upper = engine.selector_projection_upper(
                current_restore_seconds=restore_seconds,
                historical_cold_preflight_seconds=float(
                    historical_preflight["cold_preflight"]["total_seconds"]
                ),
                phase_a_prefix_size=0,
                max_phase_a_rank_seconds=max_phase_a,
                measured_phase_a_seconds=phase_a_seconds,
                exact_rebase_seconds=float(rebase_seconds),
                phase_a_end=phase_a_end,
                max_phase_b_rank_seconds=max_phase_b,
                target_size=engine.TARGET_SIZE,
            )
            combined = baseline_full / (selector_upper + float(repair_upper))
            result["stages"]["LQ4"] = {
                "status": "PASS" if combined >= 10.0 else "FAIL",
                "historical_mvsel1_baseline_seconds": baseline_full,
                "legacy_surface_compatible": True,
                "phase_a_start": 0,
                "phase_a_end": phase_a_end,
                "phase_a_measured_seconds": phase_a_seconds,
                "phase_a_max_rank_seconds": max_phase_a,
                "phase_a_prefix_digest": phase_a_prefix_digest,
                "phase_a_external_master_order_comparison": (
                    "not_applicable_no_preexisting_plan"
                ),
                "exact_rebase_seconds": rebase_seconds,
                "phase_b_sampled_ranks": len(phase_b_rows),
                "phase_b_projection_ranks_used": (
                    len(phase_b_rows) + len(optional_phase_b_rows)
                ),
                "phase_b_max_rank_seconds": max_phase_b,
                "phase_b_prefix_digest_after_sample": phase_b_sample_digest,
                "phase_b_fallback_count": sum(
                    bool(row["fallback"]) for row in phase_b_rows
                ),
                "optional_phase_b_calibration_ranks": len(optional_phase_b_rows),
                "selector_upper_seconds": selector_upper,
                "repair_upper_seconds": repair_upper,
                "combined_speedup_lower": combined,
                "minimum_10x_pass": combined >= 10.0,
                "projection_target_size": engine.TARGET_SIZE,
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
                "production_mutated": False,
            },
        )
        engine.json_dump(evidence / "worker.json", result)
        return 0 if overall == "PASS" else (2 if overall == "FAIL" else 3)
    except engine.MaterialQualificationFailure as exc:
        result.update(
            status="FAIL",
            failure_class="PRODUCT_FAILURE",
            error=f"{type(exc).__name__}: {exc}",
            elapsed_seconds=elapsed(),
        )
        engine.json_dump(evidence / "worker.json", result)
        return 2
    except Exception as exc:
        result.update(
            status="BLOCKED",
            failure_class="HARNESS_OR_INPUT_BLOCKED",
            error=f"{type(exc).__name__}: {exc}",
            elapsed_seconds=elapsed(),
        )
        engine.json_dump(evidence / "worker.json", result)
        return 3
    finally:
        if scratch_store is not None:
            try:
                scratch_store.close()
            except Exception:
                pass
        connection.close()
