from __future__ import annotations

from dataclasses import dataclass

import pytest

import mdstats

from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.target_size_study import (
    FIXED_TARGET_SIZES,
    OUTCOME_AWAITING_SHORT_SCREEN,
    OUTCOME_AWAITING_FINAL_SCREEN,
    OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
    OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
    OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
    OUTCOME_SELECTED,
    FAILURE_PHASE_TRAIN,
    STAGE_COARSE,
    STAGE_FINAL_SCREEN,
    STAGE_SHORT,
    TargetSizeStageOutcome,
    TargetSizeStudyPlan,
    TargetSizeStudyPolicy,
    TargetSizeTrainingEvidence,
    TargetSizeTrajectoryFailureEvidence,
    attach_coarse_evidence,
    attach_coarse_outcomes,
    attach_final_screen_evidence,
    attach_final_screen_outcomes,
    attach_short_evidence,
    attach_short_outcomes,
    build_target_size_study,
    materialize_candidate_prefix,
    materialize_candidate_prefix_matrix,
    materialize_selected_prefix,
)

OUTCOME_AWAITING_EPOCH_10 = OUTCOME_AWAITING_SHORT_SCREEN
OUTCOME_AWAITING_EPOCH_30 = OUTCOME_AWAITING_FINAL_SCREEN
STAGE_FINAL = STAGE_FINAL_SCREEN
attach_epoch_3_evidence = attach_coarse_evidence
attach_epoch_3_outcomes = attach_coarse_outcomes
attach_epoch_10_evidence = attach_short_evidence
attach_epoch_10_outcomes = attach_short_outcomes
attach_epoch_30_evidence = attach_final_screen_evidence
attach_epoch_30_outcomes = attach_final_screen_outcomes

# Fixed-v5 fixtures exercise the immediately preceding `(3, 10, 30)/30`
# contract through the current semantic API; they are migration/regression
# coverage, not current public aliases.
TargetSizeStudyPlan.epoch3_outcomes = property(lambda self: self.coarse_outcomes)
TargetSizeStudyPlan.epoch3_survivor_sizes = property(lambda self: self.coarse_survivor_sizes)
TargetSizeStudyPlan.epoch10_outcomes = property(lambda self: self.short_outcomes)
TargetSizeStudyPlan.epoch10_finalist_sizes = property(lambda self: self.short_finalist_sizes)
TargetSizeStudyPlan.epoch30_outcomes = property(lambda self: self.final_screen_outcomes)
TargetSizeStudyPlan.epoch3_evidence = property(lambda self: self.coarse_evidence)
TargetSizeStudyPlan.epoch10_evidence = property(lambda self: self.short_evidence)
TargetSizeStudyPlan.epoch30_evidence = property(lambda self: self.final_screen_evidence)


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
    policy = policy or TargetSizeStudyPolicy(fidelity_epochs=(3, 10, 30))
    return repair, qual, build_target_size_study(repair, qual, policy=policy, training_horizon_epochs=30)


def test_bulk_candidate_prefix_materialization_is_exported_from_top_level():
    assert mdstats.materialize_candidate_prefix_matrix is materialize_candidate_prefix_matrix
    assert "materialize_candidate_prefix_matrix" in mdstats.__all__


def test_bulk_candidate_prefix_materialization_matches_scalar_authority(monkeypatch):
    repair, _, plan = study((512, 1024, 2048), lengths=(4096, 4096))
    import mdstats.training_data.target_size_study as module

    calls = 0
    original = module._prefix_digest

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_prefix_digest", counted)
    matrix = materialize_candidate_prefix_matrix(
        plan,
        repair2=repair,
        label_domain_ids=("d0", "d1", "d0"),
        target_sizes=(512, 1024, 512),
    )
    assert calls == 4
    assert set(matrix) == {
        ("d0", 512), ("d0", 1024), ("d1", 512), ("d1", 1024)
    }
    assert matrix[("d0", 512)] == tuple(repair.domain("d0").repaired_master_order[:512])
    assert matrix[("d1", 1024)] == tuple(repair.domain("d1").repaired_master_order[:1024])


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
):
    stage = {3: "coarse", 10: "short", 30: "final_screen"}[epoch]
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


def failure(plan, size: int, seed: int, epoch: int, *, reason="nan_gradient"):
    stage = {3: STAGE_COARSE, 10: STAGE_SHORT, 30: STAGE_FINAL}[epoch]
    return TargetSizeTrajectoryFailureEvidence(
        stage=stage,
        target_size=size,
        optimizer_seed=seed,
        failure_phase=FAILURE_PHASE_TRAIN,
        failure_code="train_nonfinite_model_state",
        failure_reasons=(reason,),
        target_size_study_policy_digest=plan.policy.policy_digest,
        training_run_digest=h(f"run-{size}-seed-{seed}"),
        candidate_data_digest=plan.candidate(size).candidate_data_digest,
        training_policy_digest=h("policy"),
        schedule_digest=h("schedule"),
        execution_record_digest=h(f"execution-{size}-{seed}-{epoch}"),
        execution_attempt_digest=h(f"attempt-{size}-{seed}-{epoch}"),
        completed_epochs=max(0, epoch - 1),
        optimizer_update_count=max(0, epoch * 10 - 1),
    )


def batch(plan, sizes, epoch, scores, *, parents=None, invalid=()):
    parent_map = {} if parents is None else parents
    invalid = set(invalid)
    return tuple(
        (
            failure(plan, int(size), int(seed), epoch)
            if (int(size), int(seed)) in invalid
            else evidence(
                plan,
                int(size),
                int(seed),
                epoch,
                _score(scores, int(size), int(seed)),
                parent_map.get((int(size), int(seed))),
            )
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


def _recompute_nested_and_outer_digest(payload, outcome_field: str, index: int) -> None:
    outcome = payload[outcome_field][index]
    item = outcome["success"] if outcome.get("success") is not None else outcome["failure"]
    item.pop("content_digest", None)
    item["content_digest"] = digest(item)
    outcome.pop("content_digest", None)
    outcome["content_digest"] = digest(outcome)
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
    result = attach_epoch_3_outcomes(
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
    assert result.comparison_failures == ((8192, 2, ("train_nonfinite_model_state", "nan_gradient")),)
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
    d0_prefix = materialize_selected_prefix(
        plan, repair2=repair, label_domain_id="d0"
    )
    d1_prefix = materialize_selected_prefix(
        plan, repair2=repair, label_domain_id="d1"
    )
    assert d0_prefix == repair.domain("d0").repaired_master_order[:selected]
    assert d1_prefix == repair.domain("d1").repaired_master_order[:selected]
    assert d0_prefix != d1_prefix


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
    forged["short_outcomes"][0]["success"]["parent_checkpoint_digest"] = h("forged-parent")
    _recompute_nested_and_outer_digest(forged, "short_outcomes", 0)
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
    forged["short_outcomes"][0]["success"][field] = h(f"forged-{field}")
    _recompute_nested_and_outer_digest(forged, "short_outcomes", 0)
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
    forged["coarse_survivor_sizes"][-1] = eliminated
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
    with pytest.raises(TrainingDataInputError, match="policy digest mismatch"):
        TargetSizeStudyPlan.from_dict(forged)


def test_restart_rejects_reordered_seed_evidence_even_with_recomputed_outer_digest():
    _, _, plan = study((4096, 8192, 16384))
    plan = advance_to_epoch10(plan, {4096: 10.0, 8192: 9.8, 16384: 9.5})
    forged = plan.to_dict()
    forged["coarse_outcomes"][0], forged["coarse_outcomes"][1] = (
        forged["coarse_outcomes"][1],
        forged["coarse_outcomes"][0],
    )
    forged.pop("content_digest")
    forged["content_digest"] = digest(forged)
    with pytest.raises(TrainingDataInputError, match="policy-ordered"):
        TargetSizeStudyPlan.from_dict(forged)


def test_v5_restart_hard_rejects_legacy_schema():
    _, _, plan = study((512, 1024, 2048))
    legacy = dict(plan.to_dict())
    legacy["schema"] = "mdstats.target-size-convergence-plan.v3"
    with pytest.raises(TrainingDataSerializationError, match="not restart-compatible"):
        TargetSizeStudyPlan.from_dict(legacy)


def test_nondefault_equivalence_width_changes_policy_identity_and_ranking():
    narrow = TargetSizeStudyPolicy(
        fidelity_epochs=(3, 10, 30),
        coarse_practical_equivalence_mev_per_a=0.1,
        practical_equivalence_mev_per_a=0.1,
    )
    wide = TargetSizeStudyPolicy(
        fidelity_epochs=(3, 10, 30),
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


def test_candidate_data_digest_is_recomputed_from_canonical_candidate_inputs() -> None:
    _, _, plan = study((1024, 2048, 4096, 8192, 16384))
    payload = plan.to_dict()
    candidate = next(item for item in payload["candidates"] if item["target_size"] == 1024)
    candidate["candidate_data_digest"] = h("forged-candidate-data")
    candidate.pop("content_digest", None)
    candidate["content_digest"] = digest(candidate)
    payload.pop("content_digest", None)
    payload["content_digest"] = digest(payload)
    with pytest.raises(TrainingDataInputError, match="candidate_data_digest"):
        TargetSizeStudyPlan.from_dict(payload)


def test_too_few_comparable_candidates_at_epoch10_is_typed_terminal() -> None:
    _, _, plan = study((1024, 2048, 4096, 8192, 16384))
    plan = advance_to_epoch10(
        plan, {1024: 10.0, 2048: 9.0, 4096: 8.0, 8192: 7.0, 16384: 6.0}
    )
    sizes = plan.epoch3_survivor_sizes
    invalid = tuple((size, plan.policy.screening_optimizer_seeds[0]) for size in sizes[:-1])
    result = attach_epoch_10_outcomes(
        plan,
        batch(
            plan,
            sizes,
            10,
            {size: float(i + 1) for i, size in enumerate(sizes)},
            parents=evidence_map(plan.epoch3_evidence),
            invalid=invalid,
        ),
    )
    assert result.outcome == OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES
    assert result.comparison_failure_stage == STAGE_SHORT


def test_one_failed_finalist_at_epoch30_is_typed_terminal() -> None:
    _, _, plan = study((1024, 2048, 4096, 8192, 16384))
    plan = advance_to_epoch30(
        plan,
        {1024: 10.0, 2048: 9.0, 4096: 8.0, 8192: 7.0, 16384: 6.0},
        {1024: 10.0, 2048: 9.0, 4096: 8.0, 8192: 7.0, 16384: 6.0},
    )
    finalist = plan.epoch10_finalist_sizes[0]
    result = attach_epoch_30_outcomes(
        plan,
        batch(
            plan,
            plan.epoch10_finalist_sizes,
            30,
            {size: float(i + 1) for i, size in enumerate(plan.epoch10_finalist_sizes)},
            parents=evidence_map(plan.epoch10_evidence),
            invalid=((finalist, plan.policy.screening_optimizer_seeds[0]),),
        ),
    )
    assert result.outcome == OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES
    assert result.comparison_failure_stage == STAGE_FINAL


def test_generic_failure_code_cannot_be_target_size_scientific_evidence() -> None:
    _, _, plan = study((4096, 8192, 16384))
    size = plan.qualified_sizes[0]
    with pytest.raises(TrainingDataInputError, match="Only explicit TRAIN2 numerical codes"):
        TargetSizeTrajectoryFailureEvidence(
            stage=STAGE_COARSE,
            target_size=size,
            optimizer_seed=plan.policy.screening_optimizer_seeds[0],
            failure_phase=FAILURE_PHASE_TRAIN,
            failure_code="timeout",
            failure_reasons=("timeout",),
            target_size_study_policy_digest=plan.policy.policy_digest,
            training_run_digest=h("run"),
            candidate_data_digest=plan.candidate(size).candidate_data_digest,
            training_policy_digest=h("training-policy"),
            schedule_digest=h("schedule"),
            execution_record_digest=h("execution"),
            execution_attempt_digest=h("attempt"),
        )


def test_epoch30_replay_diagnostics_cannot_change_target_size_ranking() -> None:
    _, _, left = study((4096, 8192, 16384))
    _, _, right = study((4096, 8192, 16384))
    scores3 = {4096: 10.0, 8192: 9.8, 16384: 9.5}
    scores10 = {4096: 9.7, 8192: 9.6, 16384: 9.4}
    left = advance_to_epoch30(left, scores3, scores10)
    right = advance_to_epoch30(right, scores3, scores10)
    final_scores = {
        size: 8.0 + 0.2 * index
        for index, size in enumerate(left.epoch10_finalist_sizes)
    }

    def with_replay(plan, reverse: bool):
        raw = batch(
            plan,
            plan.epoch10_finalist_sizes,
            30,
            final_scores,
            parents=evidence_map(plan.epoch10_evidence),
        )
        rewritten = []
        for item in raw:
            payload = item.to_dict()
            payload.pop("content_digest", None)
            rank = plan.epoch10_finalist_sizes.index(item.target_size)
            payload["replay_diagnostic_force_rmse_mev_per_a"] = float(
                1000 - rank if reverse else rank + 1
            )
            payload["replay_evaluation_digest"] = h(
                f"replay-{'reverse' if reverse else 'forward'}-{item.target_size}-{item.optimizer_seed}"
            )
            rewritten.append(TargetSizeTrainingEvidence.from_dict(payload))
        return tuple(rewritten)

    left = attach_epoch_30_evidence(left, with_replay(left, False))
    right = attach_epoch_30_evidence(right, with_replay(right, True))
    assert left.outcome == OUTCOME_SELECTED
    assert right.outcome == OUTCOME_SELECTED
    assert left.selected_target_size == right.selected_target_size


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("stage", STAGE_SHORT, "stage"),
        ("optimizer_seed", 999, "policy-ordered"),
    ),
)
def test_restart_rejects_forged_failure_stage_or_seed(field, value, message) -> None:
    _, _, plan = study((4096, 8192, 16384))
    failed_key = (8192, plan.policy.screening_optimizer_seeds[0])
    terminal = attach_epoch_3_outcomes(
        plan,
        batch(
            plan,
            plan.qualified_sizes,
            3,
            {4096: 10.0, 8192: 9.0, 16384: 8.0},
            invalid=(failed_key,),
        ),
    )
    payload = terminal.to_dict()
    index = next(
        i
        for i, outcome in enumerate(payload["coarse_outcomes"])
        if outcome["failure"] is not None
    )
    payload["coarse_outcomes"][index]["failure"][field] = value
    _recompute_nested_and_outer_digest(payload, "coarse_outcomes", index)
    with pytest.raises(TrainingDataInputError, match=message):
        TargetSizeStudyPlan.from_dict(payload)
