from __future__ import annotations

import pytest

from mdstats.training_data._common import TrainingDataInputError, TrainingDataSerializationError, digest
from mdstats.training_data._target_multi_view_scoring import TargetMultiViewSelectorTelemetry
from mdstats.training_data.target_multi_view_qualification_v2 import (
    FIXED_TARGET_SIZES,
    OUTCOME_QUALIFIED,
    TargetMultiViewQualificationDomainPlanV2,
    TargetMultiViewQualificationPlanV2,
    TargetMultiViewQualificationPolicyV2,
    TargetMultiViewQualificationRungV2,
)


def _h(tag: str) -> str:
    return digest({"tag": tag})


def _telemetry() -> TargetMultiViewSelectorTelemetry:
    return TargetMultiViewSelectorTelemetry(
        uncovered_witness_count=0,
        uncovered_reference_mass=0.0,
        unique_reference_mass_fraction=0.1,
        zero_unique_candidate_fraction=0.2,
        correlation_unit_count=4,
        maximum_correlation_unit_fraction=0.25,
        run_count=4,
        condition_count=2,
    )


def _plan(qualified=(1024, 2048, 4096)) -> TargetMultiViewQualificationPlanV2:
    rows = tuple(
        TargetMultiViewQualificationRungV2(
            target_size=size,
            materializable=True,
            coverage_passed=size in qualified,
            hard_obligations_passed=size in qualified,
            qualified=size in qualified,
            coverage_report_digest=_h(f"report-{size}"),
            telemetry=_telemetry(),
            unsatisfied_obligation_ids=() if size in qualified else ("hard",),
        )
        for size in FIXED_TARGET_SIZES
    )
    domain = TargetMultiViewQualificationDomainPlanV2(
        label_domain_id="target",
        reference_domain_digest=_h("reference-domain"),
        sparse_domain_digest=_h("sparse-domain"),
        repair_domain_digest=_h("repair-domain"),
        rungs=rows,
    )
    return TargetMultiViewQualificationPlanV2(
        dataset_id="dataset",
        target_coverage_reference_digest=_h("reference"),
        target_coverage_sparse_index_digest=_h("sparse"),
        target_coverage_feasibility_digest=_h("feas"),
        target_data_role_freeze_digest=_h("role"),
        target_multi_view_repair_digest=_h("repair"),
        policy=TargetMultiViewQualificationPolicyV2(),
        domains=(domain,),
        mv_qualified_sizes=tuple(qualified),
        outcome=OUTCOME_QUALIFIED,
    )


def test_mvqual2_freezes_exact_eight_size_universe() -> None:
    policy = TargetMultiViewQualificationPolicyV2()
    assert policy.candidate_sizes == (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    with pytest.raises(TrainingDataInputError, match="freezes the production universe"):
        TargetMultiViewQualificationPolicyV2(candidate_sizes=(128, 256, 512))


def test_mvqual2_global_q_is_derived_only_from_domain_hard_evidence() -> None:
    plan = _plan()
    assert plan.mv_qualified_sizes == (1024, 2048, 4096)
    assert tuple(row.target_size for row in plan.domain("target").rungs) == FIXED_TARGET_SIZES
    with pytest.raises(TrainingDataInputError, match="global qualification"):
        TargetMultiViewQualificationPlanV2(
            dataset_id=plan.dataset_id,
            target_coverage_reference_digest=plan.target_coverage_reference_digest,
            target_coverage_sparse_index_digest=plan.target_coverage_sparse_index_digest,
            target_coverage_feasibility_digest=plan.target_coverage_feasibility_digest,
            target_data_role_freeze_digest=plan.target_data_role_freeze_digest,
            target_multi_view_repair_digest=plan.target_multi_view_repair_digest,
            policy=plan.policy,
            domains=plan.domains,
            mv_qualified_sizes=(1024,),
            outcome=OUTCOME_QUALIFIED,
        )


def test_mvqual2_roundtrip_and_legacy_schema_rejection() -> None:
    plan = _plan()
    assert TargetMultiViewQualificationPlanV2.from_dict(plan.to_dict()).content_digest == plan.content_digest
    payload = plan.to_dict()
    payload["schema"] = "mdstats.target-multi-view-qualification-plan.v1"
    with pytest.raises(TrainingDataSerializationError, match="not restart-compatible"):
        TargetMultiViewQualificationPlanV2.from_dict(payload)
