"""Shared checkpoint-started REPAIR2 execution for production and qualification.

This module contains the exact per-rung repair science used by the REV8
production seam and the lightweight production qualification harness.  It
starts from already-authenticated MVSTATE2 forward state and therefore does not
perform a fresh full-domain feasibility scan before work that will immediately
reuse a checkpoint.
"""
from __future__ import annotations

import time
from typing import Any, Mapping

from ._common import TrainingDataInputError
from .progress_timing import format_progress_time
from .target_multi_view_selector_v2 import (
    deselect_target_multi_view_candidate_v2,
    score_target_multi_view_candidate_v2,
    select_target_multi_view_candidate_v2,
)
from . import target_multi_view_repair_v2 as _repair


def repair_rung_from_authenticated_state(
    reference_domain: Any,
    forward_domain: Any,
    selection_plan: Any,
    base_rung: Any,
    *,
    policy: _repair.TargetMultiViewRepairPolicyV2,
    order: list[int],
    state: Any,
    shell_start: int,
) -> tuple[Any, dict[str, Any]]:
    """Run exact REPAIR2 science for one authenticated selector rung.

    ``state`` must already represent the complete selector prefix at the rung
    cardinality.  The helper performs no checkpoint I/O and no fresh full
    forward-problem validation.  ``state`` and ``order`` are mutated in place.
    """

    size = int(base_rung.target_size)
    shell_start = int(shell_start)
    if not base_rung.materializable:
        raise TrainingDataInputError(
            "REPAIR2 authenticated-rung helper requires a materializable rung."
        )
    if int(state.selected_count) != size:
        raise TrainingDataInputError(
            "REPAIR2 authenticated-rung state cardinality does not match target_size."
        )
    if not 0 <= shell_start <= size:
        raise TrainingDataInputError(
            "REPAIR2 authenticated-rung shell_start is invalid."
        )

    scratch = _repair._RepairProposalScratchV2(forward_domain)
    shell_size = size - shell_start
    initial_zero = sum(
        _repair._removal_metrics(order[rank], forward_domain, state)[0]
        <= policy.unique_coverage_tolerance
        for rank in range(shell_start, size)
    )
    accepted: list[Any] = []
    proposal_count = 0

    for pass_index in range(policy.max_passes_per_shell):
        changed = False
        while len(accepted) < policy.max_swaps_per_shell:
            removals: list[tuple[int, int, float, float]] = []
            for rank in range(shell_start, size):
                candidate = order[rank]
                unique, loss = _repair._removal_metrics(
                    candidate, forward_domain, state
                )
                if (
                    unique <= policy.unique_coverage_tolerance
                    and _repair._hard_safe(candidate, forward_domain, state)
                ):
                    removals.append((rank, candidate, unique, loss))
            removals.sort(
                key=lambda row: (
                    row[3],
                    -int(
                        state.correlation_unit_counts[
                            int(
                                forward_domain.candidate_correlation_unit_codes[
                                    row[1]
                                ]
                            )
                        ]
                    ),
                    reference_domain.frame_uids[row[1]],
                )
            )

            best = None
            for removal in removals[: policy.removal_shortlist_limit]:
                proposal_count += 1
                proposal = _repair._proposal(
                    reference_domain,
                    forward_domain,
                    state,
                    removal,
                    policy,
                    scratch,
                )
                if proposal is not None:
                    best = _repair._better(
                        best,
                        proposal,
                        reference_domain,
                        policy.gain_tie_tolerance,
                    )
            if best is None:
                break

            rank = int(best["rank"])
            removed = int(best["removed"])
            replacement = int(best["replacement"])
            future = next(
                (
                    index
                    for index in range(size, len(order))
                    if order[index] == replacement
                ),
                -1,
            )
            displaced = None
            if future >= size:
                order[future] = removed
                displaced = future
            order[rank] = replacement

            deselect_target_multi_view_candidate_v2(
                removed, forward_domain, state
            )
            accepted_score = score_target_multi_view_candidate_v2(
                replacement, forward_domain, state
            )
            select_target_multi_view_candidate_v2(
                replacement,
                forward_domain,
                state,
                score=accepted_score,
            )

            before = best["before"]
            after = best["after"]
            accepted.append(
                _repair.TargetMultiViewRepairSwap(
                    target_size=size,
                    pass_index=pass_index,
                    swap_index=len(accepted),
                    rank=rank,
                    removed_frame_uid=reference_domain.frame_uids[removed],
                    replacement_frame_uid=reference_domain.frame_uids[replacement],
                    removed_unique_coverage=best["unique"],
                    removed_representative_loss=best["loss"],
                    hard_deficit_before=before[0],
                    hard_deficit_after=after[0],
                    minimum_coverage_before=before[1],
                    minimum_coverage_after=after[1],
                    total_coverage_before=before[2],
                    total_coverage_after=after[2],
                    representative_utility_before=before[3],
                    representative_utility_after=after[3],
                    unit_balance_before=before[4],
                    unit_balance_after=after[4],
                    bottleneck_family_id=best["bottleneck"],
                    displaced_future_rank=displaced,
                )
            )
            changed = True
        if not changed:
            break

    coverage = tuple(
        (item.family_id, min(1.0, max(0.0, item.coverage_mass)))
        for item in state.family_states
    )
    unsatisfied = tuple(
        sorted(
            item.obligation_id
            for index, item in enumerate(forward_domain.obligations)
            if item.required
            and int(state.obligation_counts[index])
            < int(item.minimum_selected_frames)
        )
    )
    baseline_coverage = dict(base_rung.family_coverage)
    for family_id, value in coverage:
        if value + policy.gain_tie_tolerance < baseline_coverage[family_id]:
            raise TrainingDataInputError(
                "TARGET-DATA2C-REPAIR2 same-N coverage regressed below MVSEL2."
            )
    if base_rung.hard_obligations_passed and unsatisfied:
        raise TrainingDataInputError(
            "TARGET-DATA2C-REPAIR2 hard obligations regressed below MVSEL2."
        )

    rung = _repair.TargetMultiViewRepairRung(
        target_size=size,
        materializable=True,
        active_shell_start=shell_start,
        frame_uids=tuple(
            reference_domain.frame_uids[candidate] for candidate in order[:size]
        ),
        family_coverage=coverage,
        hard_obligations_passed=not unsatisfied,
        unsatisfied_obligation_ids=unsatisfied,
        hard_coverage_qualified=(
            not unsatisfied
            and all(
                value
                >= selection_plan.policy.coverage_threshold
                - policy.gain_tie_tolerance
                for _, value in coverage
            )
        ),
        swaps=tuple(accepted),
        zero_unique_shell_fraction=(
            0.0 if not shell_size else initial_zero / shell_size
        ),
    )
    return rung, {
        "proposals": proposal_count,
        "swaps": len(accepted),
        "proposal_full_state_copies": 0,
        "inverse_mutation": False,
    }


def build_repair_from_checkpoints(
    coverage_reference: Any,
    forward: Any,
    selection_plan: Any,
    *,
    policy: _repair.TargetMultiViewRepairPolicyV2,
    checkpoint_states: Mapping[str, Mapping[int, Any]],
    progress_callback: Any | None = None,
) -> _repair.TargetMultiViewRepairPlanV2:
    """Build the production REPAIR2 plan from compatible rung checkpoints.

    A fresh fully validated forward state is constructed only for the genuine
    no-checkpoint fallback.  When a compatible selector checkpoint exists, the
    exact shared rung helper starts directly from it.
    """

    domains: list[_repair.TargetMultiViewRepairDomainPlanV2] = []
    for reference_domain in coverage_reference.domains:
        started = time.monotonic()
        forward_domain = forward.domain(reference_domain.label_domain_id)
        selection_domain = selection_plan.domain(reference_domain.label_domain_id)
        uid_to_candidate = {
            uid: index for index, uid in enumerate(reference_domain.frame_uids)
        }
        order = [
            uid_to_candidate[item.frame_uid]
            for item in selection_domain.master_order
        ]
        state = None
        previous_size = 0
        rungs: list[Any] = []
        diverged = False
        proposal_count = 0
        restore_count = 0

        for base_rung in selection_domain.rungs:
            size = int(base_rung.target_size)
            if not base_rung.materializable:
                rungs.append(
                    _repair.TargetMultiViewRepairRung(
                        target_size=size,
                        materializable=False,
                        active_shell_start=previous_size,
                        unavailable_reason=(
                            base_rung.unavailable_reason
                            or "unavailable_in_mvsel2"
                        ),
                    )
                )
                continue

            shell_start = previous_size
            restored_this_rung = False
            if not diverged:
                candidate_state = checkpoint_states.get(
                    reference_domain.label_domain_id, {}
                ).get(size)
                if candidate_state is not None:
                    expected = tuple(order[:size])
                    if tuple(candidate_state.selected_order) == expected:
                        state = candidate_state
                        restored_this_rung = True
                        restore_count += 1

            if state is None:
                state = _repair.build_target_multi_view_forward_state_v2(
                    reference_domain, forward_domain
                )

            if not restored_this_rung:
                for rank in range(int(state.selected_count), size):
                    candidate = order[rank]
                    score = score_target_multi_view_candidate_v2(
                        candidate, forward_domain, state
                    )
                    select_target_multi_view_candidate_v2(
                        candidate,
                        forward_domain,
                        state,
                        score=score,
                    )

            rung, telemetry = repair_rung_from_authenticated_state(
                reference_domain,
                forward_domain,
                selection_plan,
                base_rung,
                policy=policy,
                order=order,
                state=state,
                shell_start=shell_start,
            )
            if rung.swaps:
                diverged = True
            proposal_count += int(telemetry["proposals"])
            rungs.append(rung)

            if progress_callback is not None:
                progress_callback(
                    f"status=rung; "
                    f"progress={size}/{selection_domain.rungs[-1].target_size}; "
                    f"elapsed={format_progress_time(time.monotonic() - started)}; "
                    "eta=--:--:--; "
                    f"domain={reference_domain.label_domain_id}; "
                    f"target_size={size}; active_shell_start={shell_start}; "
                    f"swaps={len(rung.swaps)}; proposals={proposal_count}; "
                    "proposal_full_state_copies=0; "
                    f"mvstate2_restore_count={restore_count}; "
                    "selected_prefix_state_mode="
                    f"{'post_divergence_carried_state' if diverged else ('mvstate2' if restored_this_rung else 'selected_prefix_forward_replay')}; "
                    "inverse_mutation=false"
                )
            previous_size = size

        domains.append(
            _repair.TargetMultiViewRepairDomainPlanV2(
                label_domain_id=reference_domain.label_domain_id,
                reference_domain_digest=reference_domain.content_digest,
                mvidx1_domain_digest=forward_domain.mvidx1_domain_digest,
                selection_domain_digest=selection_domain.content_digest,
                candidate_count=forward_domain.candidate_count,
                repaired_master_order=tuple(
                    reference_domain.frame_uids[candidate]
                    for candidate in order
                ),
                rungs=tuple(rungs),
                total_swaps=sum(len(rung.swaps) for rung in rungs),
            )
        )

    return _repair.TargetMultiViewRepairPlanV2(
        dataset_id=coverage_reference.dataset_id,
        target_coverage_reference_digest=coverage_reference.content_digest,
        mvidx1_content_digest=forward.mvidx1_content_digest,
        target_multi_view_selection_v2_digest=selection_plan.content_digest,
        policy=policy,
        domains=tuple(domains),
    )
