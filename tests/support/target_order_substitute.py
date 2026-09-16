"""Below-claim substitute for the prepare-owned target-order build.

Downstream P2/P3/campaign suites exercise split, reducer, screening,
publication and post-selection behavior on fixtures far too small for the
accepted multi-view method (0.95 coverage at ``beta=1/128`` plus canonical
obligations).  Their claims do not concern how ``pi_train`` is constructed, so
they receive this deterministic substitute in place of
``prepare_target_training_order``.  It is never a product path: the real
chain is exercised by the dedicated ``tests/test_mlff_target_order_*`` suites
(marked ``real_target_order`` where they reach ``prepare``).

The substitute order is the exact condition-balanced UID order the
pre-restoration fixtures were written against, and every configured prefix
carries passing membership evidence with no coverage families.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from mdstats.training_data._common import digest
from mdstats.training_data.target_order.preparation import TargetOrderPreparation, training_order_digest
from mdstats.training_data.target_order.qualification import (
    TargetMembershipQualificationPlan,
    TargetMembershipQualificationRung,
)
from mdstats.training_data.target_order.selector import prefix_digest
from mdstats.training_data.target_size_experiment import _condition_balanced_order


@dataclass(frozen=True)
class _RepairSummary:
    total_swaps: int = 0


@dataclass(frozen=True)
class SubstituteTargetOrderBuild:
    preparation: TargetOrderPreparation
    frame_uids: tuple[str, ...]
    qualification: TargetMembershipQualificationPlan
    repair_plan: _RepairSummary = _RepairSummary()


def substitute_target_order_build(
    population: Any,
    split: Any,
    configured_sizes: Sequence[int],
    *,
    order: Sequence[str] | None = None,
    unqualified_sizes: Sequence[int] = (),
) -> SubstituteTargetOrderBuild:
    frame_uids = (
        tuple(order)
        if order is not None
        else _condition_balanced_order(
            population, split.training_frame_uids, {uid: () for uid in split.training_frame_uids}
        )
    )
    sizes = tuple(int(v) for v in configured_sizes)
    marker = digest({"schema": "tests.substitute-target-order.v1", "split": split.content_digest, "order": list(frame_uids)})
    failing = set(int(v) for v in unqualified_sizes)
    qualification = TargetMembershipQualificationPlan(
        target_coverage_reference_digest=marker,
        obligation_authority_digest=marker,
        mvidx_content_digest=marker,
        rungs=tuple(
            TargetMembershipQualificationRung(
                target_size=size,
                frame_uids_digest=prefix_digest(frame_uids[:size]),
                family_reports=(),
                obligation_count=1,
                unsatisfied_obligation_ids=("substitute:unsatisfied",) if size in failing else (),
                mvidx_max_abs_mass_difference=0.0,
            )
            for size in sizes
        ),
    )
    preparation = TargetOrderPreparation(
        build_identity=marker,
        dataset_id=population.dataset_id,
        population_digest=population.content_digest,
        split_digest=split.content_digest,
        target_coverage_reference_digest=marker,
        obligation_authority_digest=marker,
        feasibility_report_digest=marker,
        mvidx_content_digest=marker,
        selection_plan_digest=marker,
        repair_plan_digest=marker,
        qualification_plan_digest=qualification.content_digest,
        configured_sizes=sizes,
        training_order_digest=training_order_digest(frame_uids),
        artifact_paths=(),
    )
    return SubstituteTargetOrderBuild(preparation=preparation, frame_uids=frame_uids, qualification=qualification)


def substitute_target_order_builder(policy: Any, **options: Any) -> Callable[[Any, Any], SubstituteTargetOrderBuild]:
    """``target_order_builder`` for ``build_target_size_statistical_aggregate``."""

    def build(population: Any, split: Any) -> SubstituteTargetOrderBuild:
        return substitute_target_order_build(population, split, policy.candidate_sizes, **options)

    return build


def substitute_prepare_target_order(cfg: Any, paths: Any, *, population: Any, split: Any, policy: Any, **_: Any):
    """Drop-in for ``campaign_target_size_runtime._build_current_target_training_order``."""

    return substitute_target_order_build(population, split, policy.candidate_sizes)
