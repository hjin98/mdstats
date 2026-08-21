from types import SimpleNamespace

import pytest

from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.size_fidelity2 import SizeFidelity2ExecutionPlan, SizeFidelity2Policy
from mdstats.training_data.target_multi_view_migration import build_target_multi_view_migration_plan


def _digest(char: str) -> str:
    return char * 64


def _authorities(*, size_halve2_digest: str):
    dataset_id = "mvmigrate1-contract-test"
    qualified_sizes = (2048, 4096, 8192, 16384)

    legacy = SimpleNamespace(dataset_id=dataset_id, content_digest=_digest("1"))
    repair = SimpleNamespace(dataset_id=dataset_id, content_digest=_digest("2"))
    qualification = SimpleNamespace(
        dataset_id=dataset_id,
        content_digest=_digest("3"),
        legacy_target_data_ladder_digest=legacy.content_digest,
        target_multi_view_repair_digest=repair.content_digest,
        mv_qualified_sizes=qualified_sizes,
        same_n_non_regression_passed=True,
        n95_non_regression_passed=True,
        learning_control_target_sizes=(),
    )
    size_halve2 = SimpleNamespace(
        dataset_id=dataset_id,
        content_digest=_digest("4"),
        target_multi_view_repair_digest=repair.content_digest,
        target_multi_view_qualification_digest=qualification.content_digest,
        outcome="ready_for_size_fidelity2",
    )

    policy = SizeFidelity2Policy()
    fidelity = SizeFidelity2ExecutionPlan(
        dataset_id=dataset_id,
        size_halve2_digest=size_halve2_digest,
        policy=policy,
        coverage_qualified_sizes=qualified_sizes,
        admission_widths=(4,),
        required_training_runs=tuple(
            (seed, size)
            for seed in policy.screening_seeds
            for size in qualified_sizes
        ),
    )
    return legacy, repair, qualification, size_halve2, fidelity


def test_mvmigrate1_accepts_canonical_size_fidelity2_size_halve2_digest():
    legacy, repair, qualification, size_halve2, fidelity = _authorities(
        size_halve2_digest=_digest("4")
    )

    plan = build_target_multi_view_migration_plan(
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=repair,
        target_multi_view_qualification=qualification,
        size_halve2_plan=size_halve2,
        size_fidelity2_execution_plan=fidelity,
    )

    assert plan.size_halve2_plan_digest == size_halve2.content_digest
    assert plan.size_fidelity2_execution_plan_digest == fidelity.content_digest
    assert plan.status == "awaiting_final_gpu_qualification"


def test_mvmigrate1_rejects_mismatched_size_fidelity2_size_halve2_digest():
    legacy, repair, qualification, size_halve2, fidelity = _authorities(
        size_halve2_digest=_digest("5")
    )

    with pytest.raises(
        TrainingDataInputError,
        match="SIZE-FIDELITY2 references a different SIZE-HALVE2 authority",
    ):
        build_target_multi_view_migration_plan(
            legacy_target_data_ladder=legacy,
            target_multi_view_repair=repair,
            target_multi_view_qualification=qualification,
            size_halve2_plan=size_halve2,
            size_fidelity2_execution_plan=fidelity,
        )
