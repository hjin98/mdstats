"""Internal MVSEL1/REPAIR1 oracle fixtures for MVSEL2/REPAIR2 equivalence tests.

These helpers deliberately import the retired kernels by module path.  They are
not production authorities and are not re-exported from :mod:`mdstats`.
"""
from __future__ import annotations

import mdstats
from mdstats.training_data.target_multi_view_selector import (
    TargetMultiViewSelectorPolicy,
    TargetMultiViewSelectionEntry,
    TargetMultiViewSelectionRung,
    TargetMultiViewSelectionDomainPlan,
    TargetMultiViewSelectionPlan,
    build_target_multi_view_selection_plan,
)
from tests.test_mlff_target_data2b_feas1 import _reference_and_role


def _selector(*, split_units: bool = True):
    reference, role = _reference_and_role(split_units=split_units)
    feas = mdstats.build_target_coverage_feasibility_report(reference, role)
    index = mdstats.build_target_coverage_sparse_index(reference, role, feas)
    policy = TargetMultiViewSelectorPolicy(target_sizes=(2, 4, 8, 16))
    plan = build_target_multi_view_selection_plan(reference, index, policy=policy)
    return reference, role, feas, index, policy, plan


def _index():
    reference, role = _reference_and_role(split_units=True)
    feas = mdstats.build_target_coverage_feasibility_report(reference, role)
    index = mdstats.build_target_coverage_sparse_index(reference, role, feas)
    return reference, index


def _redundant_selection():
    reference, index = _index()
    ref_domain = reference.domain("target")
    sparse = index.domain("target")
    policy = TargetMultiViewSelectorPolicy(target_sizes=(2, 4, 8, 16))
    order = tuple(range(16))
    entries = tuple(
        TargetMultiViewSelectionEntry(
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
        for sparse_family in sparse.families:
            family = ref_domain.family(sparse_family.family_id)
            coverage.append(
                (
                    sparse_family.family_id,
                    mdstats.indexed_family_covered_mass(
                        sparse_family, family.weights, selected
                    ),
                )
            )
        coverage = tuple(sorted(coverage))
        counts = mdstats.indexed_obligation_selected_counts(sparse, selected)
        unsatisfied = tuple(
            sorted(
                obligation.obligation_id
                for obligation_index, obligation in enumerate(sparse.obligations)
                if obligation.required
                and int(counts[obligation_index])
                < int(obligation.minimum_selected_frames)
            )
        )
        hard_pass = not unsatisfied
        coverage_pass = all(
            value >= policy.coverage_threshold - policy.gain_tie_tolerance
            for _, value in coverage
        )
        rungs.append(
            TargetMultiViewSelectionRung(
                target_size=size,
                materializable=True,
                frame_uids=tuple(ref_domain.frame_uids[index] for index in selected),
                family_coverage=coverage,
                hard_obligations_passed=hard_pass,
                unsatisfied_obligation_ids=unsatisfied,
                hard_coverage_qualified=hard_pass and coverage_pass,
                phase_at_boundary="hard_coverage",
            )
        )
    domain = TargetMultiViewSelectionDomainPlan(
        label_domain_id="target",
        reference_domain_digest=ref_domain.content_digest,
        sparse_domain_digest=sparse.content_digest,
        candidate_count=sparse.candidate_count,
        required_family_ids=tuple(item.family_id for item in sparse.families),
        master_order=entries,
        rungs=tuple(rungs),
        phase_a_completed_at=None,
    )
    plan = TargetMultiViewSelectionPlan(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        target_coverage_sparse_index_digest=index.content_digest,
        policy=policy,
        domains=(domain,),
    )
    return reference, index, plan
