from __future__ import annotations

import mdstats

from mdstats.training_data.campaign_cli import CampaignStore
from mdstats.training_data.target_coverage_sparse_forward_view import target_coverage_sparse_forward_view
from tests.test_mlff_target_data2c_repair1 import _redundant_selection
from tests.test_mlff_target_data2c_mvqual1 import _authorities


def test_mvmigrate2_end_to_end_and_legacy_records_remain_readable(tmp_path) -> None:
    reference, index, legacy_selection = _redundant_selection()
    forward = target_coverage_sparse_forward_view(index)
    policy = mdstats.TargetMultiViewSelectorPolicyV2(target_sizes=(2, 4, 8, 16))
    selection = mdstats.build_target_multi_view_selection_plan_v2(
        reference, forward, policy=policy, workers=2, frontier_rebuild_interval=3
    )
    mdstats.validate_target_multi_view_selection_authority_v2(
        selection,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        query_workers=2,
    )
    repair = mdstats.build_target_multi_view_repair_plan_v2(
        reference, forward, selection,
        policy=mdstats.TargetMultiViewRepairPolicyV2(max_swaps_per_shell=8),
        workers=2,
    )
    mdstats.validate_target_multi_view_repair_authority_v2(
        repair,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        target_multi_view_selection=selection,
    )
    for rung in repair.domain("target").rungs:
        if rung.materializable:
            report = mdstats.score_target_subset_coverage(
                reference, "target", rung.frame_uids, query_workers=2
            )
            assert len(report.selected_frame_uids) == rung.target_size

    legacy_repair = mdstats.build_target_multi_view_repair_plan(
        reference, index, legacy_selection,
        policy=mdstats.TargetMultiViewRepairPolicy(max_swaps_per_shell=8),
    )
    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        store.put_record("target_multi_view_selection", legacy_selection)
        store.put_record("target_multi_view_repair", legacy_repair)
        store.put_record("target_multi_view_selection_v2", selection)
        store.put_record("target_multi_view_repair_v2", repair)
        assert store.get_record("target_multi_view_selection", mdstats.TargetMultiViewSelectionPlan).content_digest == legacy_selection.content_digest
        assert store.get_record("target_multi_view_repair", mdstats.TargetMultiViewRepairPlan).content_digest == legacy_repair.content_digest
        assert store.get_record("target_multi_view_selection_v2", mdstats.TargetMultiViewSelectionPlanV2).content_digest == selection.content_digest
        assert store.get_record("target_multi_view_repair_v2", mdstats.TargetMultiViewRepairPlanV2).content_digest == repair.content_digest
    finally:
        store.close()


def test_mvmigrate2_repair_is_consumed_by_independent_mvqual() -> None:
    reference, role, feasibility, index, _, _, legacy, qualification_policy = _authorities()
    forward = target_coverage_sparse_forward_view(index)
    selection = mdstats.build_target_multi_view_selection_plan_v2(
        reference, forward,
        policy=mdstats.TargetMultiViewSelectorPolicyV2(target_sizes=(4, 8, 16, 32)),
    )
    repair = mdstats.build_target_multi_view_repair_plan_v2(reference, forward, selection)
    qualification = mdstats.build_target_multi_view_qualification_plan(
        reference, index, feasibility, role, legacy, repair,
        policy=qualification_policy,
    )
    mdstats.validate_target_multi_view_qualification_authority(
        qualification,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        target_coverage_feasibility=feasibility,
        target_data_role_freeze=role,
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        policy=qualification_policy,
    )
    assert qualification.same_n_non_regression_passed
