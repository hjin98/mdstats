from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data.campaign_cli import CampaignStore
from tests.test_mlff_target_data2b_feas1 import _reference_and_role


def _index():
    reference, role = _reference_and_role(split_units=True)
    feas = mdstats.build_target_coverage_feasibility_report(reference, role)
    index = mdstats.build_target_coverage_sparse_index(reference, role, feas)
    return reference, index


def _redundant_selection():
    reference, index = _index()
    ref_domain = reference.domain("target")
    sparse = index.domain("target")
    policy = mdstats.TargetMultiViewSelectorPolicy(target_sizes=(2, 4, 8, 16))
    # Deliberately put paired duplicates beside one another.  This is a valid
    # nested diagnostic order but is intentionally coverage-inefficient.
    order = tuple(range(16))
    entries = tuple(
        mdstats.TargetMultiViewSelectionEntry(
            rank=rank,
            frame_uid=ref_domain.frame_uids[candidate],
            phase="hard_coverage",
            primary_reason="fixture_order",
            bottleneck_family_id="target_label:paired",
            hard_obligation_gain=0,
            bottleneck_coverage_gain=0.0,
            total_coverage_gain=0.0,
            representative_gain=0.0,
            normalized_diversity=0.0,
            correlation_unit_code=int(sparse.candidate_correlation_unit_codes[candidate]),
        )
        for rank, candidate in enumerate(order)
    )
    rungs = []
    for size in policy.target_sizes:
        selected = order[:size]
        coverage = []
        for sf in sparse.families:
            family = ref_domain.family(sf.family_id)
            coverage.append((sf.family_id, mdstats.indexed_family_covered_mass(sf, family.weights, selected)))
        coverage = tuple(sorted(coverage))
        counts = mdstats.indexed_obligation_selected_counts(sparse, selected)
        unsatisfied = tuple(sorted(
            obligation.obligation_id
            for oi, obligation in enumerate(sparse.obligations)
            if obligation.required and int(counts[oi]) < int(obligation.minimum_selected_frames)
        ))
        hard_pass = not unsatisfied
        coverage_pass = all(value >= policy.coverage_threshold - policy.gain_tie_tolerance for _, value in coverage)
        rungs.append(mdstats.TargetMultiViewSelectionRung(
            target_size=size,
            materializable=True,
            frame_uids=tuple(ref_domain.frame_uids[i] for i in selected),
            family_coverage=coverage,
            hard_obligations_passed=hard_pass,
            unsatisfied_obligation_ids=unsatisfied,
            hard_coverage_qualified=hard_pass and coverage_pass,
            phase_at_boundary="hard_coverage",
        ))
    domain = mdstats.TargetMultiViewSelectionDomainPlan(
        label_domain_id="target",
        reference_domain_digest=ref_domain.content_digest,
        sparse_domain_digest=sparse.content_digest,
        candidate_count=sparse.candidate_count,
        required_family_ids=tuple(item.family_id for item in sparse.families),
        master_order=entries,
        rungs=tuple(rungs),
        phase_a_completed_at=None,
    )
    plan = mdstats.TargetMultiViewSelectionPlan(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        target_coverage_sparse_index_digest=index.content_digest,
        policy=policy,
        domains=(domain,),
    )
    return reference, index, plan


def test_repair1_performs_strict_active_shell_improvement_and_is_replayable() -> None:
    reference, index, selection = _redundant_selection()
    policy = mdstats.TargetMultiViewRepairPolicy(max_passes_per_shell=2, max_swaps_per_shell=8)
    first = mdstats.build_target_multi_view_repair_plan(reference, index, selection, policy=policy)
    second = mdstats.build_target_multi_view_repair_plan(reference, index, selection, policy=policy)
    assert first.content_digest == second.content_digest
    domain = first.domain("target")
    assert domain.total_swaps > 0
    repaired_rung = next(rung for rung in domain.rungs if rung.swaps)
    base_rung = next(rung for rung in selection.domain("target").rungs if rung.target_size == repaired_rung.target_size)
    assert all(repaired_rung.active_shell_start <= item.rank < repaired_rung.target_size for item in repaired_rung.swaps)
    assert repaired_rung.family_coverage[0][1] > base_rung.family_coverage[0][1]
    assert all(item.removed_unique_coverage <= policy.unique_coverage_tolerance for item in repaired_rung.swaps)
    assert all(item.minimum_coverage_after >= item.minimum_coverage_before for item in repaired_rung.swaps)
    mdstats.validate_target_multi_view_repair_authority(
        first,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        target_multi_view_selection=selection,
        policy=policy,
        verify_repair_replay=True,
    )


def test_repair1_freezes_lower_prefixes_and_replacement_inherits_rank() -> None:
    reference, index, selection = _redundant_selection()
    plan = mdstats.build_target_multi_view_repair_plan(reference, index, selection)
    domain = plan.domain("target")
    materialized = [r for r in domain.rungs if r.materializable]
    for lower, upper in zip(materialized, materialized[1:], strict=False):
        assert upper.frame_uids[:lower.target_size] == lower.frame_uids
    for rung in materialized:
        for swap in rung.swaps:
            assert rung.frame_uids[swap.rank] == swap.replacement_frame_uid
            assert rung.active_shell_start <= swap.rank < rung.target_size
            if swap.displaced_future_rank is not None:
                assert swap.displaced_future_rank >= rung.target_size


def test_repair1_unique_coverage_matches_scalar_leave_one_out() -> None:
    from mdstats.training_data import target_multi_view_repair as repair
    from mdstats.training_data import target_multi_view_selector as selector

    reference, index, _ = _redundant_selection()
    ref_domain = reference.domain("target")
    sparse = index.domain("target")
    state = selector._build_domain_state(ref_domain, sparse)
    selected = (0, 1, 2, 3)
    for candidate in selected:
        selector._select_and_update(candidate, sparse, state)
    family = ref_domain.family(sparse.families[0].family_id)
    full_mass = mdstats.indexed_family_covered_mass(sparse.families[0], family.weights, selected)
    for candidate in selected:
        direct = full_mass - mdstats.indexed_family_covered_mass(
            sparse.families[0], family.weights, tuple(v for v in selected if v != candidate)
        )
        observed = repair._candidate_unique_coverage(candidate, sparse, state)
        assert observed == pytest.approx(direct, abs=5.0e-15)


def test_repair1_deselect_is_exact_inverse_of_sparse_selection_update() -> None:
    from mdstats.training_data import target_multi_view_repair as repair
    from mdstats.training_data import target_multi_view_selector as selector

    reference, index, _ = _redundant_selection()
    ref_domain = reference.domain("target")
    sparse = index.domain("target")
    state = selector._build_domain_state(ref_domain, sparse)
    for candidate in (0, 1, 2, 3):
        selector._select_and_update(candidate, sparse, state)
    before = [(
        fs.coverage_mass,
        fs.covered.copy(),
        fs.multiplicity.copy(),
        fs.coverage_gain.copy(),
        fs.representative_gain.copy(),
    ) for fs in state.family_states]
    total_cov = state.total_coverage_gain.copy()
    total_rep = state.total_representative_gain.copy()
    obligations = state.obligation_counts.copy()
    hard = state.hard_gain.copy()
    units = state.unit_counts.copy()
    repair._deselect_and_update(3, sparse, state)
    selector._select_and_update(3, sparse, state)
    for fs, snapshot in zip(state.family_states, before, strict=True):
        assert fs.coverage_mass == pytest.approx(snapshot[0], abs=5.0e-15)
        assert np.array_equal(fs.covered, snapshot[1])
        assert np.array_equal(fs.multiplicity, snapshot[2])
        assert np.allclose(fs.coverage_gain, snapshot[3], atol=5.0e-13, rtol=0.0)
        assert np.allclose(fs.representative_gain, snapshot[4], atol=5.0e-13, rtol=0.0)
    assert np.allclose(state.total_coverage_gain, total_cov, atol=5.0e-13, rtol=0.0)
    assert np.allclose(state.total_representative_gain, total_rep, atol=5.0e-13, rtol=0.0)
    assert np.array_equal(state.obligation_counts, obligations)
    assert np.array_equal(state.hard_gain, hard)
    assert np.array_equal(state.unit_counts, units)


def test_repair1_round_trip_and_campaign_store(tmp_path: Path) -> None:
    reference, index, selection = _redundant_selection()
    plan = mdstats.build_target_multi_view_repair_plan(reference, index, selection)
    restored = mdstats.TargetMultiViewRepairPlan.from_dict(plan.to_dict())
    assert restored.content_digest == plan.content_digest
    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        store.put_record("target_multi_view_repair", plan)
        stored = store.get_record("target_multi_view_repair", mdstats.TargetMultiViewRepairPlan)
        assert stored.content_digest == plan.content_digest
    finally:
        store.close()


def test_repair1_detects_lineage_tampering() -> None:
    reference, index, selection = _redundant_selection()
    plan = mdstats.build_target_multi_view_repair_plan(reference, index, selection)
    payload = plan.to_dict()
    payload["target_multi_view_selection_digest"] = "f" * 64
    payload.pop("content_digest", None)
    broken = mdstats.TargetMultiViewRepairPlan.from_dict(payload)
    with pytest.raises(mdstats.TrainingDataInputError, match="selector digest"):
        mdstats.validate_target_multi_view_repair_authority(
            broken,
            target_coverage_reference=reference,
            target_coverage_sparse_index=index,
            target_multi_view_selection=selection,
        )


def test_repair1_public_api_is_exported() -> None:
    for name in (
        "TargetMultiViewRepairPolicy",
        "TargetMultiViewRepairSwap",
        "TargetMultiViewRepairRung",
        "TargetMultiViewRepairDomainPlan",
        "TargetMultiViewRepairPlan",
        "build_target_multi_view_repair_plan",
        "validate_target_multi_view_repair_authority",
    ):
        assert name in mdstats.__all__
        assert hasattr(mdstats, name)


def test_repair1_preserves_clean_mvsel_when_no_strict_swap_exists() -> None:
    from tests.test_mlff_target_data2c_mvsel1 import _selector

    reference, _, _, index, _, selection = _selector()
    plan = mdstats.build_target_multi_view_repair_plan(reference, index, selection)
    domain = plan.domain("target")
    assert domain.total_swaps == 0
    assert domain.repaired_master_order == tuple(item.frame_uid for item in selection.domain("target").master_order)
    for repaired, base in zip(domain.rungs, selection.domain("target").rungs, strict=True):
        if repaired.materializable:
            assert repaired.frame_uids == base.frame_uids
            assert tuple(k for k, _ in repaired.family_coverage) == tuple(k for k, _ in base.family_coverage)
            assert [v for _, v in repaired.family_coverage] == pytest.approx([v for _, v in base.family_coverage], abs=5.0e-15)


def test_mvsel_obligation_cache_keeps_exact_counts_for_repair_safety() -> None:
    from mdstats.training_data import target_multi_view_selector as selector

    reference, index, _ = _redundant_selection()
    ref_domain = reference.domain("target")
    sparse = index.domain("target")
    state = selector._build_domain_state(ref_domain, sparse)
    for candidate in (0, 1, 2, 3):
        selector._select_and_update(candidate, sparse, state)
    direct = mdstats.indexed_obligation_selected_counts(sparse, (0, 1, 2, 3))
    assert np.array_equal(state.obligation_counts, direct)


def test_repair1_accepts_production_style_multifamily_target_data2b(tmp_path: Path) -> None:
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    feasibility = mdstats.build_target_coverage_feasibility_report(reference, freeze, query_workers=1, query_block_size=8)
    index = mdstats.build_target_coverage_sparse_index(
        reference, freeze, feasibility, query_workers=1, query_block_size=8
    )
    candidate_min = min(len(domain.frame_uids) for domain in reference.domains)
    sizes = tuple(size for size in (2, 4, 8, 16) if size <= candidate_min)
    if not sizes:
        sizes = (candidate_min,)
    selection_policy = mdstats.TargetMultiViewSelectorPolicy(target_sizes=sizes)
    selection = mdstats.build_target_multi_view_selection_plan(reference, index, policy=selection_policy)
    repair = mdstats.build_target_multi_view_repair_plan(reference, index, selection)
    mdstats.validate_target_multi_view_repair_authority(
        repair,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        target_multi_view_selection=selection,
        verify_repair_replay=True,
    )
    assert repair.domains
    for domain in repair.domains:
        assert domain.candidate_count == len(reference.domain(domain.label_domain_id).frame_uids)
