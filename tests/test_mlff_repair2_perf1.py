from __future__ import annotations

import re

import mdstats
from mdstats.training_data.target_coverage_sparse_forward_view import target_coverage_sparse_forward_view
from mdstats.training_data.target_multi_view_repair_v2 import (
    TargetMultiViewRepairPolicyV2,
    TargetMultiViewRepairPlanV2,
    build_target_multi_view_repair_plan_v2,
    validate_target_multi_view_repair_authority_v2,
)
from mdstats.training_data.target_multi_view_selector_v2 import (
    TargetMultiViewSelectionDomainPlanV2,
    TargetMultiViewSelectionPlanV2,
    TargetMultiViewSelectorPolicyV2,
)
from tests._mlff_multiview_legacy_fixtures import _redundant_selection


def _inputs():
    reference, index, legacy_selection = _redundant_selection()
    forward = target_coverage_sparse_forward_view(index)
    legacy_domain = legacy_selection.domain("target")
    selection = TargetMultiViewSelectionPlanV2(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        mvidx1_content_digest=index.content_digest,
        policy=TargetMultiViewSelectorPolicyV2(
            target_sizes=legacy_selection.policy.target_sizes
        ),
        domains=(
            TargetMultiViewSelectionDomainPlanV2(
                label_domain_id="target",
                reference_domain_digest=legacy_domain.reference_domain_digest,
                mvidx1_domain_digest=index.domain("target").content_digest,
                candidate_count=legacy_domain.candidate_count,
                master_order=legacy_domain.master_order,
                rungs=legacy_domain.rungs,
                phase_a_completed_at=legacy_domain.phase_a_completed_at,
            ),
        ),
    )
    return reference, index, forward, selection


def _trace(plan):
    return tuple(
        swap.to_dict()
        for rung in plan.domain("target").rungs
        for swap in rung.swaps
    )


def test_repair2_r0_telemetry_is_execution_only_and_complete() -> None:
    reference, index, forward, selection = _inputs()
    policy = TargetMultiViewRepairPolicyV2()
    baseline = build_target_multi_view_repair_plan_v2(
        reference, forward, selection, policy=policy
    )
    events: list[dict[str, object]] = []
    metered = build_target_multi_view_repair_plan_v2(
        reference,
        forward,
        selection,
        policy=policy,
        telemetry_callback=events.append,
    )

    assert metered.to_dict() == baseline.to_dict()
    assert metered.content_digest == baseline.content_digest
    assert _trace(metered) == _trace(baseline)
    assert TargetMultiViewRepairPlanV2.from_dict(metered.to_dict()).content_digest == metered.content_digest
    validate_target_multi_view_repair_authority_v2(
        metered,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        target_multi_view_selection=selection,
    )

    assert events[0]["kind"] == "repair_start"
    assert events[-1]["kind"] == "repair_complete"
    rungs = [event for event in events if event["kind"] == "rung"]
    states = [event for event in events if event["kind"] == "repair_state"]
    assert rungs
    assert states
    assert any(int(event["proposal_count"]) > 0 for event in states)
    assert any(int(event["accepted_swaps"]) > 0 for event in states)

    duration = re.compile(r"^(?:\d{2,}):\d{2}:\d{2}$|^--:--:--$")
    for event in states:
        for key in (
            "removal_metric_scan_wall_hhmmss",
            "representative_objective_wall_hhmmss",
            "proposal_frontier_state_invariant_wall_hhmmss",
            "removed_witness_mark_wall_hhmmss",
            "unit_filter_wall_hhmmss",
            "removal_dependent_representative_diversity_wall_hhmmss",
            "accepted_mutation_wall_hhmmss",
            "eta_hhmmss",
        ):
            assert duration.match(str(event[key]))
        assert int(event["zero_unique_hard_safe_removals"]) >= int(event["removal_shortlist_size"])
        assert int(event["coverage_gain_candidate_family_rows"]) >= 0
        assert int(event["coverage_gain_forward_edges"]) >= 0
        resource_delta = event["resource_delta"]
        if resource_delta is not None:
            assert all(int(value) >= 0 for value in resource_delta.values())
