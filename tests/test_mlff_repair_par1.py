from __future__ import annotations

import numpy as np

import mdstats
from mdstats.training_data import target_multi_view_repair as repair
from mdstats.training_data import target_multi_view_selector as selector
from tests.test_mlff_target_data2c_repair1 import _redundant_selection


def _selected_repair_state():
    reference, index, selection = _redundant_selection()
    ref_domain = reference.domain("target")
    sparse_domain = index.domain("target")
    state = selector._build_domain_state(ref_domain, sparse_domain)
    order = [ref_domain.frame_index(item.frame_uid) for item in selection.domain("target").master_order]
    for candidate in order[:8]:
        selector._select_and_update(candidate, sparse_domain, state)
    return reference, index, selection, ref_domain, sparse_domain, state, order


def test_repair_par1_complete_trace_is_worker_count_invariant() -> None:
    reference, index, selection = _redundant_selection()
    policy = mdstats.TargetMultiViewRepairPolicy(max_passes_per_shell=2, max_swaps_per_shell=8)
    scalar = mdstats.build_target_multi_view_repair_plan(
        reference, index, selection, policy=policy, execution_mode="reference"
    )
    for workers in (1, 2, 4):
        optimized = mdstats.build_target_multi_view_repair_plan(
            reference, index, selection, policy=policy, proposal_workers=workers
        )
        assert optimized.to_dict() == scalar.to_dict()
        assert optimized.content_digest == scalar.content_digest


def test_repair_par1_vectorized_proposal_matches_scalar_candidate_swap() -> None:
    _, _, _, ref_domain, sparse_domain, state, order = _selected_repair_state()
    policy = mdstats.TargetMultiViewRepairPolicy(max_passes_per_shell=2, max_swaps_per_shell=8)
    _, removals = repair._shell_removal_scan(
        ref_domain, sparse_domain, state, order, 4, 8, policy
    )
    assert removals
    representative_utility = repair._representative_utility(ref_domain, state)
    scratch = repair._RepairProposalScratch(sparse_domain)
    for removal in removals:
        scalar = repair._candidate_swap(
            ref_domain, sparse_domain, state, removal, representative_utility, policy
        )
        scratch.mark_removed(sparse_domain, int(removal[1]))
        vectorized = repair._candidate_swap(
            ref_domain,
            sparse_domain,
            state,
            removal,
            representative_utility,
            policy,
            proposal_scratch=scratch,
        )
        assert vectorized == scalar


def test_repair_par1_fused_removal_metrics_match_scalar_definitions() -> None:
    _, _, _, _, sparse_domain, state, order = _selected_repair_state()
    for candidate in order[:8]:
        unique = 0.0
        loss = 0.0
        for sparse_family, family_state in zip(
            sparse_domain.families, state.family_states, strict=True
        ):
            witnesses = np.asarray(sparse_family.candidate_witness_indices(candidate), dtype=np.int64)
            if witnesses.size == 0:
                continue
            multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
            weights = family_state.weights[witnesses]
            mask = multiplicity == 1.0
            if np.any(mask):
                unique += float(np.sum(weights[mask], dtype=np.float64))
            loss += float(np.sum(weights / multiplicity, dtype=np.float64))
        observed = repair._candidate_removal_metrics(candidate, sparse_domain, state)
        assert observed == (unique, loss)


def test_repair_par1_inverse_rank_map_preserves_future_displacement() -> None:
    reference, index, selection = _redundant_selection()
    policy = mdstats.TargetMultiViewRepairPolicy(max_passes_per_shell=2, max_swaps_per_shell=8)
    plan = mdstats.build_target_multi_view_repair_plan(
        reference, index, selection, policy=policy, proposal_workers=4
    )
    domain = plan.domain("target")
    for rung in domain.rungs:
        for swap in rung.swaps:
            assert rung.frame_uids[swap.rank] == swap.replacement_frame_uid
            if swap.displaced_future_rank is not None:
                assert swap.displaced_future_rank >= rung.target_size


def test_repair_par1_campaign_template_exposes_execution_only_worker_control() -> None:
    from mdstats.training_data import campaign_cli

    source = __import__("pathlib").Path(campaign_cli.__file__).read_text()
    assert "target_multi_view_repair_workers = 0" in source
    assert "_target_multi_view_repair_parallelism" in source
    assert "proposal_workers=repair_workers" in source
