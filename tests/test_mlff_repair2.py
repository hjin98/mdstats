from __future__ import annotations

import pytest

import mdstats
from mdstats.training_data.target_coverage_sparse_forward_view import target_coverage_sparse_forward_view

from mdstats.training_data.target_multi_view_selector import (
    TargetMultiViewSelectorPolicy as LegacySelectorPolicy,
    build_target_multi_view_selection_plan as build_legacy_selection_plan,
)
from mdstats.training_data.target_multi_view_repair import (
    TargetMultiViewRepairPolicy as LegacyRepairPolicy,
    build_target_multi_view_repair_plan as build_legacy_repair_plan,
)

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
from tests._mlff_multiview_legacy_fixtures import _redundant_selection


def _trace(plan, domain_id="target"):
    """Return the complete persisted REPAIR1 swap authority in canonical order."""

    return tuple(
        (
            swap.target_size,
            swap.pass_index,
            swap.swap_index,
            swap.rank,
            swap.removed_frame_uid,
            swap.replacement_frame_uid,
            swap.removed_unique_coverage,
            swap.removed_representative_loss,
            swap.hard_deficit_before,
            swap.hard_deficit_after,
            swap.minimum_coverage_before,
            swap.minimum_coverage_after,
            swap.total_coverage_before,
            swap.total_coverage_after,
            swap.representative_utility_before,
            swap.representative_utility_after,
            swap.unit_balance_before,
            swap.unit_balance_after,
            swap.bottleneck_family_id,
            swap.displaced_future_rank,
        )
        for rung in plan.domain(domain_id).rungs
        for swap in rung.swaps
    )


def _policy_payload_without_authority(policy):
    payload = policy.to_dict().copy()
    payload.pop("schema", None)
    payload.pop("policy_digest", None)
    payload.pop("authority_version", None)
    return payload


def test_repair2_default_policy_is_exact_repair1_semantic_mirror() -> None:
    legacy = LegacyRepairPolicy()
    forward = TargetMultiViewRepairPolicyV2()
    assert _policy_payload_without_authority(forward) == _policy_payload_without_authority(legacy)


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("unique_coverage_tolerance", 0.0),
        ("unique_coverage_tolerance", 1.0e-9),
        ("gain_tie_tolerance", 0.0),
        ("gain_tie_tolerance", 1.0e-9),
        ("max_passes_per_shell", 0),
        ("max_passes_per_shell", 17),
        ("max_swaps_per_shell", 0),
        ("max_swaps_per_shell", 1025),
        ("removal_shortlist_limit", 0),
        ("removal_shortlist_limit", 4097),
        ("active_shell_only", False),
        ("replacement_rank_inheritance", False),
        ("strict_no_coverage_regression", False),
        ("clustering_score_authority", "scientific"),
    ),
)
def test_repair2_policy_validation_matches_repair1_fail_closed_contract(field: str, invalid) -> None:
    legacy_kwargs = {field: invalid}
    forward_kwargs = {field: invalid}
    with pytest.raises(mdstats.TrainingDataInputError):
        LegacyRepairPolicy(**legacy_kwargs)
    with pytest.raises(mdstats.TrainingDataInputError):
        TargetMultiViewRepairPolicyV2(**forward_kwargs)


def test_repair2_matches_legacy_trace_and_is_schedule_invariant() -> None:
    reference, index, forward = _forward_fixture()
    sizes = (4, 8, 12, 16)
    legacy_selection = build_legacy_selection_plan(
        reference, index, policy=LegacySelectorPolicy(target_sizes=sizes)
    )
    legacy = build_legacy_repair_plan(
        reference, index, legacy_selection,
        policy=LegacyRepairPolicy(max_passes_per_shell=2, max_swaps_per_shell=8),
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


def test_repair2_reproduces_nonempty_legacy_repair_trace_under_default_policy() -> None:
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
    legacy = build_legacy_repair_plan(
        reference,
        index,
        legacy_selection,
        policy=LegacyRepairPolicy(),
        execution_mode="reference",
    )
    repaired = build_target_multi_view_repair_plan_v2(
        reference,
        forward,
        selection,
        policy=TargetMultiViewRepairPolicyV2(),
    )
    assert legacy.domain("target").total_swaps > 0
    assert _trace(repaired) == _trace(legacy)
    assert repaired.domain("target").repaired_master_order == legacy.domain("target").repaired_master_order
    validate_target_multi_view_repair_authority_v2(
        repaired,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        target_multi_view_selection=selection,
    )
