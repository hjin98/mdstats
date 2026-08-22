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
    OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
    OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
    OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
    OUTCOME_SELECTED,
    TargetSizeStudyPlan,
    TargetSizeStudyPolicy,
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


def study(qualified=FIXED_TARGET_SIZES, lengths=(20000, 20000), *, policy=None):
    repair = Repair(lengths)
    qual = Qual(repair, qualified)
    return repair, qual, build_target_size_study(repair, qual, policy=policy)


def _score(scores, size: int, seed: int) -> float:
    if (size, seed) in scores:
        return float(scores[(size, seed)])
    return float(scores[size])


def evidence(
    plan,
    size: int,
    seed: int,
    epoch: int,
    score: float,
    parent=None,
    *,
    numerical_valid=True,
    failure_reasons=(),
):
    stage = {3: "coarse", 10: "short", 30: "final"}[epoch]
    kwargs = dict(
        stage=stage,
        target_size=size,
        optimizer_seed=seed,
        completed_epochs=epoch,
        planned_epochs=30,
        optimizer_update_count=epoch * 10,
        structures_presented=epoch * size,
        normalized_schedule_progress={3: 0.1, 10: 1.0 / 3.0, 30: 1.0}[epoch],
        instantaneous_learning_rate=1.0e-3,
        wall_time_seconds=float(epoch),
        target_force_score_mev_per_a=score,
        numerical_valid=bool(numerical_valid),
        foundation_identity_digest=h("foundation"),
        evaluation_role_digest=h("role"),
        training_policy_digest=h("policy"),
        target_size_study_policy_digest=plan.policy.policy_digest,
        training_run_digest=h(f"run-{size}-seed-{seed}"),
        candidate_data_digest=plan.candidate(size).candidate_data_digest,
        checkpoint_digest=h(f"checkpoint-{size}-{seed}-{epoch}"),
        schedule_digest=h("schedule"),
        optimizer_state_digest=h(f"optimizer-{size}-{seed}-{epoch}"),
        rng_state_digest=h(f"rng-{size}-{seed}-{epoch}"),
        target_evaluation_digest=h(f"target-eval-{size}-{seed}-{epoch}"),
        failure_reasons=tuple(failure_reasons),
    )
    if epoch == 30:
        kwargs.update(
            replay_diagnostic_force_rmse_mev_per_a=8.0,
            replay_evaluation_digest=h(f"replay-{size}-{seed}"),
        )
    if parent is not None:
        kwargs.update(
            parent_checkpoint_digest=parent.checkpoint_digest,
            parent_optimizer_state_digest=parent.optimizer_state_digest,
            parent_rng_state_digest=parent.rng_state_digest,
        )
    return TargetSizeTrainingEvidence(**kwargs)


def batch(plan, sizes, epoch, scores, *, parents=None, invalid=()):
    parent_map = {} if parents is None else parents
    invalid = set(invalid)
    return tuple(
        evidence(
            plan,
            int(size),
            int(seed),
            epoch,
            _score(scores, int(size), int(seed)),
            parent_map.get((int(size), int(seed))),
            numerical_valid=(int(size), int(seed)) not in invalid,
            failure_reasons=("nan_gradient",) if (int(size), int(seed)) in invalid else (),
        )
        for size in sizes
        for seed in plan.policy.screening_optimizer_seeds
    )


def evidence_map(items):
    return {(v.target_size, v.optimizer_seed): v for v in items}


def advance_to_epoch10(plan, scores):
    return attach_epoch_3_evidence(
        plan, batch(plan, plan.qualified_sizes, 3, scores)
    )


def advance_to_epoch30(plan, scores3, scores10):
    plan = advance_to_epoch10(plan, scores3)
    return attach_epoch_10_evidence(
        plan,
        batch(
            plan,
            plan.epoch3_survivor_sizes,
            10,
            scores10,
            parents=evidence_map(plan.epoch3_evidence),
        ),
    )


def select(plan, scores30):
    return attach_epoch_30_evidence(
        plan,
        batch(
            plan,
            plan.epoch10_finalist_sizes,
            30,
            scores30,
            parents=evidence_map(plan.epoch10_evidence),
        ),
    )


def _recompute_nested_and_outer_digest(payload, evidence_field: str, index: int) -> None:
    item = payload[evidence_field][index]
    item.pop("content_digest", None)
    item["content_digest"] = digest(item)
    payload.pop("content_digest", None)
    payload["content_digest"] = digest(payload)


def _recompute_policy_and_outer_digest(payload) -> None:
    policy = payload["policy"]
    policy.pop("policy_digest", None)
    policy["policy_digest"] = digest(policy)
    payload.pop("content_digest", None)
    payload["content_digest"] = digest(payload)


def test_fixed_universe_and_q3_exact_funnel():
    _, _, plan = study((4096, 8192, 16384))
    assert tuple(v.target_size for v in plan.candidates) == FIXED_TARGET_SIZES
    assert plan.policy.screening_optimizer_seeds == (1, 2)
    plan = advance_to_epoch10(plan, {4096: 20.0, 8192: 18.0, 16384: 17.5})
    assert plan.outcome == OUTCOME_AWAITING_EPOCH_10
    assert len(plan.epoch3_survivor_sizes) == 3
    assert tuple((v.target_size, v.optimizer_seed) for v in plan.epoch3_evidence) == tuple(
        (size, seed)
        for size in plan.qualified_sizes
        for seed in plan.policy.screening_optimizer_seeds
    )
    plan = attach_epoch_10_evidence(
        plan,
        batch(
            plan,
            plan.epoch3_survivor_sizes,
            10,
            {size: 10.0 + i for i, size in enumerate(plan.epoch3_survivor_sizes)},
            parents=evidence_map(plan.epoch3_evidence),
        ),
    )
    assert plan.outcome == OUTCOME_AWAITING_EPOCH_30
    assert len(plan.epoch10_finalist_sizes) == 2
    plan = select(
        plan,
        {
            size: 8.0 + i * 2.0
            for i, size in enumerate(plan.epoch10_finalist_sizes)
        },
    )
    assert plan.outcome == OUTCOME_SELECTED
    assert plan.selected_target_size in plan.epoch10_finalist_sizes


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
    e10 = list(
        batch(
            plan,
            plan.epoch3_survivor_sizes,
            10,
            {size: 8.0 + i for i, size in enumerate(plan.epoch3_survivor_sizes)},
            parents=evidence_map(plan.epoch3_evidence),
        )
    )
    first = e10[0]
    payload = first.to_dict()
    payload.pop("schema")
    payload.pop("content_digest")
    payload["failure_reasons"] = tuple(payload["failure_reasons"])
    payload["parent_checkpoint_digest"] = h("wrong-parent")
    e10[0] = TargetSizeTrainingEvidence(**payload)
    with pytest.raises(TrainingDataInputError, match="checkpoint ancestry"):
        attach_epoch_10_evidence(plan, e10)


def test_screening_prefers_smaller_sizes_inside_equivalence_band():
    _, _, plan = study((1024, 2048, 4096, 8192, 16384))
    plan = advance_to_epoch10(
        plan,
        {1024: 10.0, 2048: 10.1, 4096: 10.2, 8192: 10.3, 16384: 10.4},
    )
    assert plan.epoch3_survivor_sizes == (1024, 2048, 4096, 8192)
    assert 16384 not in plan.epoch3_survivor_sizes


def test_paired_seed_aggregate_controls_ranking_not_single_seed():
    _, _, plan = study((4096, 8192, 16384))
    scores = {
        (4096, 1): 5.0,
        (4096, 2): 15.0,
        (8192, 1): 8.0,
        (8192, 2): 8.0,
        (16384, 1): 9.0,
        (16384, 2): 9.0,
    }
    plan = advance_to_epoch10(plan, scores)
    # Paired means are 10, 8, and 9. With epsilon=1, 8192 and 16384 share
    # the best band and smaller 8192 ranks first.
    assert plan.epoch3_survivor_sizes[:2] == (8192, 16384)


def test_final_equivalence_prefers_smaller_candidate_and_freezes_selection():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    smaller = min(plan.epoch10_finalist_sizes)
    scores = {size: (8.0 if size == smaller else 7.4) for size in plan.epoch10_finalist_sizes}
    plan = select(plan, scores)
    assert plan.outcome == OUTCOME_SELECTED
    assert plan.selected_target_size == smaller
    with pytest.raises(TrainingDataInputError):
        attach_epoch_30_evidence(plan, plan.epoch30_evidence)


def test_fixed_ceiling_material_improvement_is_terminal_nonconvergence():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 20.0, 8192: 10.0, 16384: 9.5},
        {4096: 20.0, 8192: 10.0, 16384: 9.5},
    )
    other = next(v for v in plan.epoch10_finalist_sizes if v != 16384)
    plan = select(plan, {other: 12.0, 16384: 8.0})
    assert plan.outcome == OUTCOME_NONCONVERGED_AT_FIXED_CEILING
    assert plan.selected_target_size is None
    assert "rescue above 16384 is forbidden" in plan.decision_reason


def test_insufficient_paired_comparability_is_typed_terminal_state():
    _, _, plan = study((4096, 8192, 16384))
    result = attach_epoch_3_evidence(
        plan,
        batch(
            plan,
            plan.qualified_sizes,
            3,
            {4096: 10.0, 8192: 9.0, 16384: 8.0},
            invalid=((8192, 2),),
        ),
    )
    assert result.outcome == OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES
    assert result.comparison_failure_stage == "coarse"
    assert result.comparison_failures == ((8192, 2, ("nan_gradient",)),)
    restored = TargetSizeStudyPlan.from_dict(result.to_dict())
    assert restored.content_digest == result.content_digest


def test_selected_production_prefix_is_exact_and_unavailable_before_selection():
    repair, _, plan = study((4096, 8192, 16384))
    with pytest.raises(TrainingDataInputError, match="before target-size selection"):
        materialize_selected_prefix(plan, repair2=repair, label_domain_id="d0")
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    plan = select(
        plan,
        {size: 9.0 + i * 0.2 for i, size in enumerate(plan.epoch10_finalist_sizes)},
    )
    selected = plan.selected_target_size
    assert materialize_selected_prefix(
        plan, repair2=repair, label_domain_id="d0"
    ) == repair.domain("d0").repaired_master_order[:selected]


def test_v5_restart_round_trip_revalidates_exact_continuation_semantics():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    restored = TargetSizeStudyPlan.from_dict(plan.to_dict())
    assert restored.content_digest == plan.content_digest

    forged = plan.to_dict()
    forged["epoch10_evidence"][0]["parent_checkpoint_digest"] = h("forged-parent")
    _recompute_nested_and_outer_digest(forged, "epoch10_evidence", 0)
    with pytest.raises(TrainingDataInputError, match="checkpoint ancestry"):
        TargetSizeStudyPlan.from_dict(forged)


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("parent_optimizer_state_digest", "optimizer ancestry"),
        ("parent_rng_state_digest", "RNG ancestry"),
    ),
)
def test_restart_rejects_forged_optimizer_and_rng_continuation(field, message):
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    forged = plan.to_dict()
    forged["epoch10_evidence"][0][field] = h(f"forged-{field}")
    _recompute_nested_and_outer_digest(forged, "epoch10_evidence", 0)
    with pytest.raises(TrainingDataInputError, match=message):
        TargetSizeStudyPlan.from_dict(forged)


def test_restart_rejects_forged_survivor_decision_after_digest_recomputation():
    _, _, plan = study((1024, 2048, 4096, 8192, 16384))
    plan = advance_to_epoch10(
        plan,
        {1024: 10.0, 2048: 10.1, 4096: 10.2, 8192: 10.3, 16384: 12.0},
    )
    eliminated = next(size for size in plan.qualified_sizes if size not in plan.epoch3_survivor_sizes)
    forged = plan.to_dict()
    forged["epoch3_survivor_sizes"][-1] = eliminated
    forged.pop("content_digest", None)
    forged["content_digest"] = digest(forged)
    with pytest.raises(TrainingDataInputError, match="survivor decision"):
        TargetSizeStudyPlan.from_dict(forged)


def test_restart_rejects_forged_selected_size_after_digest_recomputation():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    plan = select(
        plan,
        {size: 8.0 + i * 0.4 for i, size in enumerate(plan.epoch10_finalist_sizes)},
    )
    other = next(size for size in plan.epoch10_finalist_sizes if size != plan.selected_target_size)
    forged = plan.to_dict()
    forged["selected_target_size"] = other
    forged.pop("content_digest", None)
    forged["content_digest"] = digest(forged)
    with pytest.raises(TrainingDataInputError, match="Selected target size"):
        TargetSizeStudyPlan.from_dict(forged)


def test_restart_rejects_rebound_equivalence_policy_with_old_evidence():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch10(plan, {4096: 10.0, 8192: 9.8, 16384: 9.5})
    forged = plan.to_dict()
    forged["policy"]["coarse_practical_equivalence_mev_per_a"] = 0.5
    _recompute_policy_and_outer_digest(forged)
    with pytest.raises(TrainingDataInputError, match="different target-size study policy"):
        TargetSizeStudyPlan.from_dict(forged)


def test_restart_rejects_reordered_seed_evidence_even_with_recomputed_outer_digest():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch10(plan, {4096: 10.0, 8192: 9.8, 16384: 9.5})
    forged = plan.to_dict()
    forged["epoch3_evidence"][0], forged["epoch3_evidence"][1] = (
        forged["epoch3_evidence"][1],
        forged["epoch3_evidence"][0],
    )
    forged.pop("content_digest")
    forged["content_digest"] = digest(forged)
    with pytest.raises(TrainingDataInputError, match="exact ordered"):
        TargetSizeStudyPlan.from_dict(forged)


def test_v5_restart_hard_rejects_legacy_schema():
    _, _, plan = study((512, 1024, 2048))
    legacy = dict(plan.to_dict())
    legacy["schema"] = "mdstats.target-size-convergence-plan.v3"
    with pytest.raises(TrainingDataSerializationError, match="not restart-compatible"):
        TargetSizeStudyPlan.from_dict(legacy)


def test_nondefault_equivalence_width_changes_policy_identity_and_ranking():
    narrow = TargetSizeStudyPolicy(
        coarse_practical_equivalence_mev_per_a=0.1,
        practical_equivalence_mev_per_a=0.1,
    )
    wide = TargetSizeStudyPolicy(
        coarse_practical_equivalence_mev_per_a=1.0,
        practical_equivalence_mev_per_a=1.0,
    )
    assert narrow.policy_digest != wide.policy_digest
    _, _, narrow_plan = study((1024, 2048, 4096, 8192, 16384), policy=narrow)
    _, _, wide_plan = study((1024, 2048, 4096, 8192, 16384), policy=wide)
    scores = {1024: 10.0, 2048: 9.7, 4096: 9.6, 8192: 9.5, 16384: 9.4}
    narrow_plan = advance_to_epoch10(narrow_plan, scores)
    wide_plan = advance_to_epoch10(wide_plan, scores)
    assert narrow_plan.epoch3_survivor_sizes != wide_plan.epoch3_survivor_sizes
    assert wide_plan.epoch3_survivor_sizes == (1024, 2048, 4096, 8192)


def test_epoch30_does_not_apply_second_hard_gate_after_mvqual():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
        {4096: 10.0, 8192: 9.8, 16384: 9.5},
    )
    finalists = tuple(plan.epoch10_finalist_sizes)
    smaller = min(finalists)
    final_evidence = batch(
        plan,
        finalists,
        30,
        {size: 8.0 if size == smaller else 8.5 for size in finalists},
        parents=evidence_map(plan.epoch10_evidence),
    )
    assert all(not hasattr(v, "target_hard_gates_passed") for v in final_evidence)
    selected = attach_epoch_30_evidence(plan, final_evidence)
    assert selected.outcome == OUTCOME_SELECTED
    assert selected.selected_target_size == smaller
