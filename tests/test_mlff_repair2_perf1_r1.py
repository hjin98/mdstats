from __future__ import annotations

import numpy as np

from mdstats.training_data import target_multi_view_repair_v2 as repair
from mdstats.training_data.target_multi_view_selector_v2 import (
    build_target_multi_view_forward_state_v2,
    score_target_multi_view_candidate_v2,
    select_target_multi_view_candidate_v2,
)
from tests.test_mlff_repair2_perf1 import _inputs


def _first_proposal_state():
    reference, _, forward, selection = _inputs()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    selection_domain = selection.domain("target")
    uid_to_candidate = {uid: index for index, uid in enumerate(reference_domain.frame_uids)}
    order = [uid_to_candidate[item.frame_uid] for item in selection_domain.master_order]
    state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    policy = repair.TargetMultiViewRepairPolicyV2()
    previous_size = 0
    for base_rung in selection_domain.rungs:
        if not base_rung.materializable:
            continue
        size = int(base_rung.target_size)
        for rank in range(previous_size, size):
            candidate = order[rank]
            score = score_target_multi_view_candidate_v2(candidate, forward_domain, state)
            select_target_multi_view_candidate_v2(candidate, forward_domain, state, score=score)
        removals = []
        for rank in range(previous_size, size):
            candidate = order[rank]
            unique, loss = repair._removal_metrics(candidate, forward_domain, state)
            if unique <= policy.unique_coverage_tolerance and repair._hard_safe(
                candidate, forward_domain, state
            ):
                removals.append((rank, candidate, unique, loss))
        removals.sort(key=lambda row: (
            row[3],
            -int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[row[1]])]),
            reference_domain.frame_uids[row[1]],
        ))
        shortlist = removals[: policy.removal_shortlist_limit]
        if shortlist:
            return reference_domain, forward_domain, state, policy, shortlist
        previous_size = size
    raise AssertionError("fixture did not produce a REPAIR2 proposal state")


def test_repair2_r1_frontier_matches_frozen_scalar_proposal_oracle() -> None:
    reference_domain, forward_domain, state, policy, shortlist = _first_proposal_state()
    context = repair._build_proposal_frontier_context_v2(forward_domain, state, policy)

    # The shared context is deliberately O(candidate_count): no candidate×family
    # matrix or removal×candidate table is retained between proposals.
    assert isinstance(context.candidates, tuple)
    assert len(context.candidates) <= forward_domain.candidate_count
    assert not any(
        isinstance(getattr(context, name), np.ndarray)
        for name in context.__dataclass_fields__
    )

    for removal in shortlist:
        reference = repair._proposal_reference(
            reference_domain,
            forward_domain,
            state,
            removal,
            policy,
            repair._RepairProposalScratchV2(forward_domain),
        )
        factored = repair._proposal_from_frontier_context_v2(
            reference_domain,
            forward_domain,
            state,
            removal,
            policy,
            repair._RepairProposalScratchV2(forward_domain),
            context,
        )
        assert factored == reference


def test_repair2_r1_builds_frontier_once_per_unchanged_state() -> None:
    reference, _, forward, selection = _inputs()
    events: list[dict[str, object]] = []
    plan = repair.build_target_multi_view_repair_plan_v2(
        reference,
        forward,
        selection,
        telemetry_callback=events.append,
    )
    assert plan.domain("target").total_swaps > 0

    states = [event for event in events if event["kind"] == "repair_state"]
    proposal_states = [event for event in states if int(event["proposal_count"]) > 0]
    assert proposal_states
    assert any(int(event["proposal_count"]) > 1 for event in proposal_states)
    for event in proposal_states:
        assert int(event["frontier_build_count"]) == 1
        assert 0 <= int(event["proposal_evaluation_count"]) <= int(event["proposal_count"])
        assert int(event["coverage_gain_candidate_family_rows"]) == (
            int(event["frontier_coverage_gain_candidate_family_rows"])
            + int(event["proposal_final_coverage_candidate_family_rows"])
        )
        assert int(event["coverage_gain_forward_edges"]) == (
            int(event["frontier_coverage_gain_forward_edges"])
            + int(event["proposal_final_coverage_forward_edges"])
        )

    # The state-invariant scan is shared, rather than repeated once per logical
    # removal proposal. This is the structural acceptance condition for R1.
    multi = next(event for event in proposal_states if int(event["proposal_count"]) > 1)
    assert int(multi["frontier_build_count"]) == 1
    assert int(multi["frontier_coverage_gain_candidate_family_rows"]) > 0
