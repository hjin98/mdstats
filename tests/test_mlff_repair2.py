from __future__ import annotations

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
    build_target_multi_view_selection_plan_v2,
)
from tests.test_mlff_mvsel2_forward import _forward_fixture
from tests.test_mlff_target_data2c_repair1 import _redundant_selection


def _trace(plan, domain_id="target"):
    return tuple(
        (swap.target_size, swap.pass_index, swap.swap_index, swap.rank,
         swap.removed_frame_uid, swap.replacement_frame_uid, swap.displaced_future_rank)
        for rung in plan.domain(domain_id).rungs for swap in rung.swaps
    )


def test_repair2_matches_legacy_trace_and_is_schedule_invariant() -> None:
    reference, index, forward = _forward_fixture()
    sizes = (4, 8, 12, 16)
    legacy_selection = mdstats.build_target_multi_view_selection_plan(
        reference, index, policy=mdstats.TargetMultiViewSelectorPolicy(target_sizes=sizes)
    )
    legacy = mdstats.build_target_multi_view_repair_plan(
        reference, index, legacy_selection,
        policy=mdstats.TargetMultiViewRepairPolicy(max_passes_per_shell=2, max_swaps_per_shell=8),
        execution_mode="reference",
    )
    selection = build_target_multi_view_selection_plan_v2(
        reference, forward, policy=TargetMultiViewSelectorPolicyV2(target_sizes=sizes)
    )
    policy = TargetMultiViewRepairPolicyV2(max_passes_per_shell=2, max_swaps_per_shell=8)
    scalar = build_target_multi_view_repair_plan_v2(
        reference, forward, selection, policy=policy, workers=1, batch_size=1
    )
    scheduled = build_target_multi_view_repair_plan_v2(
        reference, forward, selection, policy=policy, workers=4, batch_size=7
    )
    assert _trace(scalar) == _trace(scheduled)
    assert _trace(scalar) == _trace(legacy)
    assert TargetMultiViewRepairPlanV2.from_dict(scalar.to_dict()).content_digest == scalar.content_digest
    for base, repaired in zip(selection.domain("target").rungs, scalar.domain("target").rungs, strict=True):
        if repaired.materializable:
            assert repaired.hard_obligations_passed or not base.hard_obligations_passed
            assert all(value + 1.0e-14 >= dict(base.family_coverage)[family]
                       for family, value in repaired.family_coverage)


def test_repair2_source_has_no_inverse_or_mvsel1_execution_dependency() -> None:
    from mdstats.training_data import target_multi_view_repair_v2 as module

    source = open(module.__file__, encoding="utf-8").read()
    assert "witness_candidates" not in source
    assert "witness_offsets" not in source
    assert "_select_and_update" not in source
    assert "target_multi_view_selector import" not in source


def test_repair2_reproduces_nonempty_legacy_repair_trace() -> None:
    reference, index, legacy_selection = _redundant_selection()
    forward = target_coverage_sparse_forward_view(index)
    legacy_domain = legacy_selection.domain("target")
    selection = TargetMultiViewSelectionPlanV2(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        mvidx1_content_digest=index.content_digest,
        policy=TargetMultiViewSelectorPolicyV2(target_sizes=legacy_selection.policy.target_sizes),
        domains=(TargetMultiViewSelectionDomainPlanV2(
            label_domain_id="target",
            reference_domain_digest=legacy_domain.reference_domain_digest,
            mvidx1_domain_digest=index.domain("target").content_digest,
            candidate_count=legacy_domain.candidate_count,
            master_order=legacy_domain.master_order,
            rungs=legacy_domain.rungs,
            phase_a_completed_at=legacy_domain.phase_a_completed_at,
        ),),
    )
    legacy_policy = mdstats.TargetMultiViewRepairPolicy(max_passes_per_shell=2, max_swaps_per_shell=8)
    legacy = mdstats.build_target_multi_view_repair_plan(
        reference, index, legacy_selection, policy=legacy_policy, execution_mode="reference"
    )
    repaired = build_target_multi_view_repair_plan_v2(
        reference, forward, selection,
        policy=TargetMultiViewRepairPolicyV2(max_passes_per_shell=2, max_swaps_per_shell=8),
    )
    assert legacy.domain("target").total_swaps > 0
    assert _trace(repaired) == _trace(legacy)
    validate_target_multi_view_repair_authority_v2(
        repaired,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        target_multi_view_selection=selection,
    )
