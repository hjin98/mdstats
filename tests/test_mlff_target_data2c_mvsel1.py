from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from mdstats.training_data.campaign_cli import CampaignStore
from tests.test_mlff_target_data2b_feas1 import _reference_and_role


def _selector(*, split_units: bool = True):
    reference, role = _reference_and_role(split_units=split_units)
    feas = mdstats.build_target_coverage_feasibility_report(reference, role)
    index = mdstats.build_target_coverage_sparse_index(reference, role, feas)
    policy = mdstats.TargetMultiViewSelectorPolicy(target_sizes=(2, 4, 8, 16))
    plan = mdstats.build_target_multi_view_selection_plan(reference, index, policy=policy)
    return reference, role, feas, index, policy, plan


def test_mvsel1_is_deterministic_nested_and_exactly_replayable() -> None:
    reference, _, _, index, policy, first = _selector()
    second = mdstats.build_target_multi_view_selection_plan(reference, index, policy=policy)
    assert first.content_digest == second.content_digest
    domain = first.domain("target")
    assert len(domain.master_order) == 16
    assert len({item.frame_uid for item in domain.master_order}) == 16
    assert domain.phase_a_completed_at == 8
    assert [item.target_size for item in domain.rungs] == [2, 4, 8, 16]
    assert [item.hard_coverage_qualified for item in domain.rungs] == [False, False, True, True]
    assert domain.rungs[0].frame_uids == tuple(item.frame_uid for item in domain.master_order[:2])
    assert set(domain.rungs[0].frame_uids).issubset(domain.rungs[1].frame_uids)
    assert set(domain.rungs[1].frame_uids).issubset(domain.rungs[2].frame_uids)
    assert set(domain.rungs[2].frame_uids).issubset(domain.rungs[3].frame_uids)
    assert domain.master_order[0].primary_reason == "hard_obligation_gain"
    assert all(item.phase == "representative_fill" for item in domain.master_order[8:])
    mdstats.validate_target_multi_view_selection_authority(
        first,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        policy=policy,
        verify_selection_replay=True,
    )


def test_mvsel1_services_hard_obligations_before_coverage_only_candidates() -> None:
    reference, _, _, index, policy, plan = _selector()
    domain = plan.domain("target")
    sparse = index.domain("target")
    uid_to_index = {uid: i for i, uid in enumerate(reference.domain("target").frame_uids)}
    first_two = [uid_to_index[item.frame_uid] for item in domain.master_order[:2]]
    counts = mdstats.indexed_obligation_selected_counts(sparse, first_two)
    required = [
        i for i, item in enumerate(sparse.obligations)
        if item.required
    ]
    # The first two frames jointly satisfy the rare/extent/correlation hard
    # obligations in this fixture even though global 95% coverage still fails.
    assert all(counts[i] >= sparse.obligations[i].minimum_selected_frames for i in required)
    assert domain.rungs[0].hard_obligations_passed
    assert not domain.rungs[0].hard_coverage_qualified


def test_mvsel1_phase_b_uses_diminishing_representative_gain() -> None:
    _, _, _, _, _, plan = _selector()
    domain = plan.domain("target")
    phase_b = domain.master_order[8:]
    assert phase_b
    assert all(item.primary_reason == "density_aware_representative_fill" for item in phase_b)
    assert all(item.representative_gain >= 0.0 for item in phase_b)
    # Repeated representation has diminishing utility after every witness is
    # already covered; later exact duplicates cannot gain more than the first
    # representative-fill choice in this symmetric paired fixture.
    assert phase_b[-1].representative_gain <= phase_b[0].representative_gain + 1.0e-14


def test_mvsel1_round_trip_and_campaign_store(tmp_path: Path) -> None:
    reference, _, _, index, policy, plan = _selector()
    restored = mdstats.TargetMultiViewSelectionPlan.from_dict(plan.to_dict())
    assert restored.content_digest == plan.content_digest
    store = CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        store.put_record("target_multi_view_selection", plan)
        stored = store.get_record("target_multi_view_selection", mdstats.TargetMultiViewSelectionPlan)
        assert stored.content_digest == plan.content_digest
        mdstats.validate_target_multi_view_selection_authority(
            stored,
            target_coverage_reference=reference,
            target_coverage_sparse_index=index,
            policy=policy,
        )
    finally:
        store.close()


def test_mvsel1_detects_lineage_and_rung_tampering() -> None:
    reference, _, _, index, policy, plan = _selector()
    payload = plan.to_dict()
    payload["target_coverage_sparse_index_digest"] = "f" * 64
    payload.pop("content_digest", None)
    broken = mdstats.TargetMultiViewSelectionPlan.from_dict(payload)
    with pytest.raises(mdstats.TrainingDataInputError, match="sparse-index digest"):
        mdstats.validate_target_multi_view_selection_authority(
            broken,
            target_coverage_reference=reference,
            target_coverage_sparse_index=index,
            policy=policy,
        )


def test_mvsel1_public_api_is_exported() -> None:
    for name in (
        "TargetMultiViewSelectorPolicy",
        "TargetMultiViewSelectionEntry",
        "TargetMultiViewSelectionRung",
        "TargetMultiViewSelectionDomainPlan",
        "TargetMultiViewSelectionPlan",
        "build_target_multi_view_selection_plan",
        "validate_target_multi_view_selection_authority",
    ):
        assert name in mdstats.__all__
        assert hasattr(mdstats, name)


def test_mvsel1_incremental_gains_match_direct_sparse_recomputation() -> None:
    import numpy as np
    from mdstats.training_data import target_multi_view_selector as mvsel

    reference, _, _, index, policy, _ = _selector()
    ref_domain = reference.domain("target")
    sparse_domain = index.domain("target")
    state = mvsel._build_domain_state(ref_domain, sparse_domain)
    selected: list[int] = []
    for _ in range(6):
        chosen, _, _, _ = mvsel._choose_candidate(ref_domain, sparse_domain, state, policy)
        selected.append(chosen)
        mvsel._select_and_update(chosen, sparse_domain, state)
        for sparse_family, family_state in zip(sparse_domain.families, state.family_states, strict=True):
            family = ref_domain.family(sparse_family.family_id)
            covered = mdstats.indexed_family_covered_mask(sparse_family, selected)
            direct_mass = float(np.sum(np.asarray(family.weights)[covered], dtype=np.float64))
            assert family_state.coverage_mass == pytest.approx(direct_mass, abs=5.0e-15)
            for candidate in np.flatnonzero(state.available):
                direct_gain = mdstats.indexed_family_marginal_gain(
                    sparse_family, family.weights, covered, int(candidate)
                )
                assert family_state.coverage_gain[candidate] == pytest.approx(direct_gain, abs=5.0e-13)
                witnesses = sparse_family.candidate_witness_indices(int(candidate))
                direct_rep = float(np.sum(
                    np.asarray(family.weights)[witnesses]
                    / (1.0 + family_state.multiplicity[witnesses]),
                    dtype=np.float64,
                ))
                assert family_state.representative_gain[candidate] == pytest.approx(direct_rep, abs=5.0e-13)
