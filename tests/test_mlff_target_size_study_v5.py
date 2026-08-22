from __future__ import annotations

from dataclasses import dataclass

import pytest

from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.target_size_study import (
    FIXED_TARGET_SIZES,
    OUTCOME_AWAITING_EPOCH_10,
    OUTCOME_AWAITING_EPOCH_30,
    OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
    OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
    OUTCOME_SELECTED,
    TargetSizeStudyPlan,
    TargetSizeTrainingEvidence,
    attach_epoch_10_evidence,
    attach_epoch_30_evidence,
    attach_epoch_3_evidence,
    build_target_size_study,
    materialize_candidate_prefix,
    materialize_selected_prefix,
)


def h(tag: str) -> str:
    return digest({"tag": tag})


@dataclass(frozen=True)
class Domain:
    label_domain_id: str
    repaired_master_order: tuple[str, ...]


class Repair:
    def __init__(self, lengths=(20000, 20000)):
        self.dataset_id = "dataset"
        self.domains = tuple(
            Domain(f"d{i}", tuple(f"d{i}-u{j}" for j in range(n)))
            for i, n in enumerate(lengths)
        )
        self.content_digest = h("repair-" + "-".join(str(v) for v in lengths))
        self._domains = {v.label_domain_id: v for v in self.domains}

    def domain(self, label_domain_id: str) -> Domain:
        return self._domains[label_domain_id]


class Qual:
    def __init__(self, repair: Repair, qualified):
        self.dataset_id = repair.dataset_id
        self.target_multi_view_repair_digest = repair.content_digest
        self.mv_qualified_sizes = tuple(qualified)
        self.content_digest = h("qual-" + "-".join(str(v) for v in qualified))


def study(qualified=FIXED_TARGET_SIZES, lengths=(20000, 20000)):
    repair = Repair(lengths)
    qual = Qual(repair, qualified)
    return repair, qual, build_target_size_study(repair, qual)


def evidence(plan, size: int, epoch: int, score: float, parent=None, *, final_pass=True):
    stage = {3: "coarse", 10: "short", 30: "final"}[epoch]
    kwargs = dict(
        stage=stage,
        target_size=size,
        optimizer_seed=1,
        completed_epochs=epoch,
        planned_epochs=30,
        optimizer_update_count=epoch * 10,
        structures_presented=epoch * size,
        normalized_schedule_progress={3: 0.1, 10: 1.0 / 3.0, 30: 1.0}[epoch],
        instantaneous_learning_rate=1.0e-3,
        wall_time_seconds=float(epoch),
        target_force_score_mev_per_a=score,
        numerical_valid=True,
        target_hard_gates_passed=bool(final_pass) if epoch == 30 else True,
        foundation_identity_digest=h("foundation"),
        evaluation_role_digest=h("role"),
        training_policy_digest=h("policy"),
        training_run_digest=h(f"run-{size}"),
        candidate_data_digest=plan.candidate(size).candidate_data_digest,
        checkpoint_digest=h(f"checkpoint-{size}-{epoch}"),
        schedule_digest=h("schedule"),
        optimizer_state_digest=h(f"optimizer-{size}-{epoch}"),
        rng_state_digest=h(f"rng-{size}-{epoch}"),
        target_evaluation_digest=h(f"target-eval-{size}-{epoch}"),
    )
    if epoch == 30:
        kwargs.update(
            replay_diagnostic_force_rmse_mev_per_a=8.0,
            replay_evaluation_digest=h(f"replay-{size}"),
            replay_admissible=bool(final_pass),
            physical_qualification_passed=bool(final_pass),
            physical_qualification_digest=h(f"physical-{size}"),
        )
    if parent is not None:
        kwargs.update(
            parent_checkpoint_digest=parent.checkpoint_digest,
            parent_optimizer_state_digest=parent.optimizer_state_digest,
            parent_rng_state_digest=parent.rng_state_digest,
        )
    return TargetSizeTrainingEvidence(**kwargs)


def advance_to_epoch10(plan, scores):
    return attach_epoch_3_evidence(
        plan,
        [evidence(plan, size, 3, scores[size]) for size in plan.qualified_sizes],
    )


def advance_to_epoch30(plan, scores3, scores10):
    plan = advance_to_epoch10(plan, scores3)
    parents = {v.target_size: v for v in plan.epoch3_evidence}
    return attach_epoch_10_evidence(
        plan,
        [evidence(plan, size, 10, scores10[size], parents[size]) for size in plan.epoch3_survivor_sizes],
    )


def test_fixed_universe_and_q3_exact_funnel():
    _, _, plan = study((4096, 8192, 16384))
    assert tuple(v.target_size for v in plan.candidates) == FIXED_TARGET_SIZES
    plan = advance_to_epoch10(plan, {4096: 20.0, 8192: 18.0, 16384: 17.5})
    assert plan.outcome == OUTCOME_AWAITING_EPOCH_10
    assert len(plan.epoch3_survivor_sizes) == 3
    parents = {v.target_size: v for v in plan.epoch3_evidence}
    plan = attach_epoch_10_evidence(
        plan,
        [evidence(plan, size, 10, 10.0 + i, parents[size]) for i, size in enumerate(plan.epoch3_survivor_sizes)],
    )
    assert plan.outcome == OUTCOME_AWAITING_EPOCH_30
    assert len(plan.epoch10_finalist_sizes) == 2


def test_q_below_three_is_terminal_without_rescue():
    _, _, plan = study((8192, 16384))
    assert plan.outcome == OUTCOME_INSUFFICIENT_QUALIFIED_SIZES
    assert plan.complete
    assert plan.next_training_sizes == ()


def test_mvqual_qualified_prefix_must_materialize():
    repair = Repair((20000, 9000))
    qual = Qual(repair, (8192, 16384))
    with pytest.raises(TrainingDataInputError, match="cannot materialize"):
        build_target_size_study(repair, qual)


def test_candidate_membership_is_exact_repair2_prefix():
    repair, _, plan = study((512, 1024, 2048))
    assert materialize_candidate_prefix(
        plan, repair2=repair, label_domain_id="d0", target_size=1024
    ) == repair.domain("d0").repaired_master_order[:1024]


def test_epoch10_requires_exact_checkpoint_optimizer_rng_continuation():
    _, _, plan = study((2048, 4096, 8192, 16384))
    plan = advance_to_epoch10(plan, {2048: 13.0, 4096: 12.0, 8192: 11.0, 16384: 10.5})
    parents = {v.target_size: v for v in plan.epoch3_evidence}
    e10 = [evidence(plan, size, 10, 8.0 + i, parents[size]) for i, size in enumerate(plan.epoch3_survivor_sizes)]
    first = e10[0]
    payload = first.to_dict()
    payload.pop("schema")
    payload.pop("content_digest")
    payload["failure_reasons"] = tuple(payload["failure_reasons"])
    payload["parent_checkpoint_digest"] = h("wrong-parent")
    e10[0] = TargetSizeTrainingEvidence(**payload)
    with pytest.raises(TrainingDataInputError, match="checkpoint ancestry"):
        attach_epoch_10_evidence(plan, e10)


def test_screening_preserves_fixed_ceiling_inside_equivalence_band():
    _, _, plan = study((2048, 4096, 8192, 16384))
    plan = advance_to_epoch10(plan, {2048: 10.0, 4096: 10.2, 8192: 10.3, 16384: 10.4})
    assert 16384 in plan.epoch3_survivor_sizes
    parents = {v.target_size: v for v in plan.epoch3_evidence}
    plan = attach_epoch_10_evidence(
        plan,
        [evidence(plan, size, 10, 10.0 + 0.1 * i, parents[size]) for i, size in enumerate(plan.epoch3_survivor_sizes)],
    )
    assert 16384 in plan.epoch10_finalist_sizes


def test_final_equivalence_prefers_smaller_candidate_and_freezes_selection():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    parents = {v.target_size: v for v in plan.epoch10_evidence}
    smaller = min(plan.epoch10_finalist_sizes)
    finals = [
        evidence(plan, size, 30, {smaller: 8.0, 16384: 7.4}[size], parents[size])
        for size in plan.epoch10_finalist_sizes
    ]
    plan = attach_epoch_30_evidence(plan, finals)
    assert plan.outcome == OUTCOME_SELECTED
    assert plan.selected_target_size == smaller
    with pytest.raises(TrainingDataInputError):
        attach_epoch_30_evidence(plan, finals)


def test_fixed_ceiling_material_improvement_is_terminal_nonconvergence():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 20.0, 8192: 10.0, 16384: 9.5},
        {4096: 20.0, 8192: 10.0, 16384: 9.5},
    )
    parents = {v.target_size: v for v in plan.epoch10_evidence}
    other = next(v for v in plan.epoch10_finalist_sizes if v != 16384)
    plan = attach_epoch_30_evidence(
        plan,
        [
            evidence(plan, other, 30, 12.0, parents[other]),
            evidence(plan, 16384, 30, 8.0, parents[16384]),
        ],
    )
    assert plan.outcome == OUTCOME_NONCONVERGED_AT_FIXED_CEILING
    assert plan.selected_target_size is None
    assert "rescue above 16384 is forbidden" in plan.decision_reason


def test_selected_production_prefix_is_exact_and_unavailable_before_selection():
    repair, _, plan = study((4096, 8192, 16384))
    with pytest.raises(TrainingDataInputError, match="before target-size selection"):
        materialize_selected_prefix(plan, repair2=repair, label_domain_id="d0")
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    parents = {v.target_size: v for v in plan.epoch10_evidence}
    plan = attach_epoch_30_evidence(
        plan,
        [evidence(plan, size, 30, 9.0 + i * 0.2, parents[size]) for i, size in enumerate(plan.epoch10_finalist_sizes)],
    )
    selected = plan.selected_target_size
    assert materialize_selected_prefix(
        plan, repair2=repair, label_domain_id="d0"
    ) == repair.domain("d0").repaired_master_order[:selected]


def test_v5_restart_hard_rejects_legacy_schema_and_round_trips_current_schema():
    _, _, plan = study((512, 1024, 2048))
    restored = TargetSizeStudyPlan.from_dict(plan.to_dict())
    assert restored.content_digest == plan.content_digest
    legacy = dict(plan.to_dict())
    legacy["schema"] = "mdstats.target-size-convergence-plan.v3"
    with pytest.raises(TrainingDataSerializationError, match="not restart-compatible"):
        TargetSizeStudyPlan.from_dict(legacy)
