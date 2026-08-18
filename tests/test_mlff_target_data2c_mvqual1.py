from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from mdstats.training_data.campaign_cli import CampaignStore
from tests.test_mlff_target_data2c_ladder import _reference_and_role


def _authorities(n: int = 40):
    reference, role = _reference_and_role(n)
    feasibility = mdstats.build_target_coverage_feasibility_report(reference, role)
    sparse = mdstats.build_target_coverage_sparse_index(reference, role, feasibility)
    selector_policy = mdstats.TargetMultiViewSelectorPolicy(target_sizes=(4, 8, 16, 32))
    selection = mdstats.build_target_multi_view_selection_plan(reference, sparse, policy=selector_policy)
    repair = mdstats.build_target_multi_view_repair_plan(reference, sparse, selection)
    ladder_policy = mdstats.TargetDataLadderPolicy(
        ladder_exponents=(2, 3, 4, 5), minimum_materializable_rungs=3
    )
    legacy = mdstats.build_target_data_ladder(
        reference, role, policy=ladder_policy, minimum_coverage_qualifiers=1
    )
    qualification_policy = mdstats.TargetMultiViewQualificationPolicy(
        coverage_threshold=reference.policy.coverage_threshold,
        capacity_ceiling=32,
    )
    return reference, role, feasibility, sparse, selection, repair, legacy, qualification_policy


def _inefficient_repair(reference, sparse, *, target_sizes=(4, 8, 16, 32)):
    ref_domain = reference.domain("target")
    sparse_domain = sparse.domain("target")
    selector_policy = mdstats.TargetMultiViewSelectorPolicy(target_sizes=target_sizes)
    order = tuple(range(max(target_sizes)))
    entries = tuple(
        mdstats.TargetMultiViewSelectionEntry(
            rank=rank,
            frame_uid=ref_domain.frame_uids[candidate],
            phase="hard_coverage",
            primary_reason="mvqual1_bad_fixture",
            bottleneck_family_id=sparse_domain.families[0].family_id,
            hard_obligation_gain=0,
            bottleneck_coverage_gain=0.0,
            total_coverage_gain=0.0,
            representative_gain=0.0,
            normalized_diversity=0.0,
            correlation_unit_code=int(sparse_domain.candidate_correlation_unit_codes[candidate]),
        )
        for rank, candidate in enumerate(order)
    )
    rungs = []
    for size in target_sizes:
        selected = order[:size]
        family_coverage = tuple(sorted(
            (
                sf.family_id,
                mdstats.indexed_family_covered_mass(
                    sf, ref_domain.family(sf.family_id).weights, selected
                ),
            )
            for sf in sparse_domain.families
        ))
        counts = mdstats.indexed_obligation_selected_counts(sparse_domain, selected)
        unsatisfied = tuple(sorted(
            obligation.obligation_id
            for oi, obligation in enumerate(sparse_domain.obligations)
            if obligation.required
            and int(counts[oi]) < int(obligation.minimum_selected_frames)
        ))
        hard_pass = not unsatisfied
        coverage_pass = all(
            value >= selector_policy.coverage_threshold - selector_policy.gain_tie_tolerance
            for _, value in family_coverage
        )
        rungs.append(mdstats.TargetMultiViewSelectionRung(
            target_size=size,
            materializable=True,
            frame_uids=tuple(ref_domain.frame_uids[i] for i in selected),
            family_coverage=family_coverage,
            hard_obligations_passed=hard_pass,
            unsatisfied_obligation_ids=unsatisfied,
            hard_coverage_qualified=hard_pass and coverage_pass,
            phase_at_boundary="hard_coverage",
        ))
    domain = mdstats.TargetMultiViewSelectionDomainPlan(
        label_domain_id="target",
        reference_domain_digest=ref_domain.content_digest,
        sparse_domain_digest=sparse_domain.content_digest,
        candidate_count=sparse_domain.candidate_count,
        required_family_ids=tuple(sf.family_id for sf in sparse_domain.families),
        master_order=entries,
        rungs=tuple(rungs),
        phase_a_completed_at=None,
    )
    selection = mdstats.TargetMultiViewSelectionPlan(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        target_coverage_sparse_index_digest=sparse.content_digest,
        policy=selector_policy,
        domains=(domain,),
    )
    return mdstats.build_target_multi_view_repair_plan(
        reference,
        sparse,
        selection,
        policy=mdstats.TargetMultiViewRepairPolicy(
            max_swaps_per_shell=1, removal_shortlist_limit=4
        ),
    )


def test_mvqual1_independently_qualifies_same_n_non_regression_and_replays() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities()
    first = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair, policy=policy
    )
    second = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair, policy=policy
    )
    assert first.content_digest == second.content_digest
    assert first.global_common_target_sizes == (4, 8, 16, 32)
    assert first.same_n_non_regression_passed
    assert first.n95_non_regression_passed
    assert first.legacy_n95_common == 32
    assert first.mv_n95_common == 32
    assert first.mv_qualified_sizes == (32,)
    assert first.learning_control_target_sizes == (32,)
    assert first.learning_control_status == "deferred_final_gpu_qualification"
    assert first.outcome == "scientific_coverage_qualified_learning_controls_deferred"
    assert all(item.same_n_qualified for item in first.domains[0].comparisons)
    mdstats.validate_target_multi_view_qualification_authority(
        first,
        target_coverage_reference=reference,
        target_coverage_sparse_index=sparse,
        target_coverage_feasibility=feasibility,
        target_data_role_freeze=role,
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        policy=policy,
        verify_replay=True,
    )


def test_mvqual1_rejects_worse_same_n_selector_without_tuning() -> None:
    reference, role, feasibility, sparse, _, _, legacy, policy = _authorities()
    inefficient = _inefficient_repair(reference, sparse)
    plan = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, inefficient, policy=policy
    )
    assert plan.outcome == "same_n_nonregression_failed"
    assert not plan.same_n_non_regression_passed
    comparison = plan.domains[0].comparisons[-1]
    assert comparison.target_size == 32
    assert comparison.legacy_passed
    assert not comparison.mv_passed
    assert comparison.mv_d_max > comparison.legacy_d_max
    assert not comparison.same_n_qualified


def test_mvqual1_tracks_hard_obligations_and_independent_coverage_telemetry() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities()
    plan = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair, policy=policy
    )
    comparisons = plan.domains[0].comparisons
    assert any(not item.legacy_hard_obligations_passed for item in comparisons)
    assert all(
        item.mv_telemetry.uncovered_reference_mass <= item.legacy_telemetry.uncovered_reference_mass + 1.0e-12
        for item in comparisons
    )
    final = comparisons[-1]
    assert final.legacy_hard_obligations_passed
    assert final.mv_hard_obligations_passed
    assert final.mv_telemetry.zero_unique_candidate_fraction <= final.legacy_telemetry.zero_unique_candidate_fraction
    assert final.mv_telemetry.correlation_unit_count >= 1
    assert final.mv_telemetry.run_count >= 1
    assert final.mv_telemetry.condition_count >= 1


def test_mvqual1_round_trip_and_campaign_store(tmp_path: Path) -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities()
    plan = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair, policy=policy
    )
    restored = mdstats.TargetMultiViewQualificationPlan.from_dict(plan.to_dict())
    assert restored.content_digest == plan.content_digest
    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        store.put_record("target_multi_view_qualification", plan)
        stored = store.get_record(
            "target_multi_view_qualification", mdstats.TargetMultiViewQualificationPlan
        )
        assert stored.content_digest == plan.content_digest
    finally:
        store.close()


def test_mvqual1_fails_closed_on_lineage_drift() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities()
    plan = mdstats.build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair, policy=policy
    )
    payload = plan.to_dict()
    payload["target_multi_view_repair_digest"] = "f" * 64
    payload.pop("content_digest", None)
    broken = mdstats.TargetMultiViewQualificationPlan.from_dict(payload)
    with pytest.raises(mdstats.TrainingDataInputError, match="lineage"):
        mdstats.validate_target_multi_view_qualification_authority(
            broken,
            target_coverage_reference=reference,
            target_coverage_sparse_index=sparse,
            target_coverage_feasibility=feasibility,
            target_data_role_freeze=role,
            legacy_target_data_ladder=legacy,
            target_multi_view_repair=repair,
            policy=policy,
        )


def test_mvqual1_public_api_is_exported() -> None:
    for name in (
        "TargetMultiViewQualificationPolicy",
        "TargetMultiViewQualificationRung",
        "TargetMultiViewQualificationPlan",
        "build_target_multi_view_qualification_plan",
        "validate_target_multi_view_qualification_authority",
    ):
        assert name in mdstats.__all__
        assert hasattr(mdstats, name)


def test_mvqual1_is_bound_into_prepare_receipt_and_contract() -> None:
    from mdstats.training_data import campaign_cli

    assert "target_multi_view_qualification" in campaign_cli._PREPARE_RECEIPT_RECORD_KEYS
    contract = campaign_cli._prepare_contract_signature()
    assert contract["target_data2c_mvqual1_version"] == mdstats.TARGET_MULTI_VIEW_QUALIFICATION_VERSION
    assert contract["target_data2c_mvidx1_version"] == mdstats.TARGET_COVERAGE_SPARSE_INDEX_VERSION
    assert contract["target_data2c_mvsel1_version"] == mdstats.TARGET_MULTI_VIEW_SELECTOR_VERSION
    assert contract["target_data2c_repair1_version"] == mdstats.TARGET_MULTI_VIEW_REPAIR_VERSION
    assert callable(campaign_cli._ensure_target_multi_view_qualification)
