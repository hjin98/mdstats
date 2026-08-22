from __future__ import annotations

import mdstats

from mdstats.training_data.campaign_cli import CampaignStore
from mdstats.training_data.target_coverage_sparse_forward_view import (
    target_coverage_sparse_forward_view,
)
from tests._mlff_multiview_legacy_fixtures import _redundant_selection


def test_mvsel2_repair2_current_records_roundtrip_and_authenticate(tmp_path) -> None:
    reference, index, _ = _redundant_selection()
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
        reference,
        forward,
        selection,
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

    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        store.put_record("target_multi_view_selection_v2", selection)
        store.put_record("target_multi_view_repair_v2", repair)
        restored_selection = store.get_record(
            "target_multi_view_selection_v2", mdstats.TargetMultiViewSelectionPlanV2
        )
        restored_repair = store.get_record(
            "target_multi_view_repair_v2", mdstats.TargetMultiViewRepairPlanV2
        )
        assert restored_selection.content_digest == selection.content_digest
        assert restored_repair.content_digest == repair.content_digest
    finally:
        store.close()
