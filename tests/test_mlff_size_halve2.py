from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data._common import digest

SIZES = mdstats.SIZE_HALVE2_FIXED_TARGET_SIZES


@dataclass(frozen=True)
class _Rung:
    target_size: int
    materializable: bool = True

    def to_dict(self):
        return {
            "schema": "test.repair-rung.v1",
            "target_size": self.target_size,
            "materializable": self.materializable,
        }


def _upstream(*, qualified=SIZES, nonregression=True, unavailable=()):
    domains = []
    for label in ("a", "b"):
        domains.append(SimpleNamespace(
            label_domain_id=label,
            rungs=tuple(_Rung(size, size not in set(unavailable)) for size in SIZES),
        ))
    repair_digest = digest({"repair": tuple(qualified), "unavailable": tuple(unavailable)})
    repair = SimpleNamespace(dataset_id="synthetic", domains=tuple(domains), content_digest=repair_digest)
    qual = SimpleNamespace(
        dataset_id="synthetic",
        target_multi_view_repair_digest=repair_digest,
        content_digest=digest({"qual": tuple(qualified), "nonregression": nonregression}),
        mv_qualified_sizes=tuple(qualified),
        same_n_non_regression_passed=bool(nonregression),
        n95_non_regression_passed=bool(nonregression),
    )
    return repair, qual


def _ev(size: int, score: float, *, stage: str, parent=None, numerical=True, target_gate=True, replay_ok=True, physical_ok=True):
    epochs = {"coarse": 3, "short": 10, "final": 30}[stage]
    kwargs = dict(
        stage=stage,
        target_size=size,
        optimizer_seed=1,
        completed_epochs=epochs,
        planned_epochs=30,
        optimizer_update_count=epochs * 100,
        structures_presented=epochs * size,
        normalized_schedule_progress=epochs / 30.0,
        instantaneous_learning_rate=1.0e-6 if stage == "final" else 5.0e-5,
        wall_time_seconds=float(size),
        target_force_score_mev_per_a=float(score),
        numerical_valid=bool(numerical),
        target_hard_gates_passed=bool(target_gate),
        foundation_identity_digest=digest({"foundation": 1}),
        evaluation_role_digest=digest({"role": 1}),
        training_policy_digest=digest({"policy": 1}),
        training_run_digest=digest({"run": size}),
        checkpoint_digest=digest({"ckpt": stage, "size": size}),
        schedule_digest=digest({"schedule": 1}),
        optimizer_state_digest=digest({"opt": stage, "size": size}),
        rng_state_digest=digest({"rng": stage, "size": size}),
        target_evaluation_digest=digest({"target": stage, "size": size}),
    )
    if stage == "short":
        kwargs.update(
            parent_checkpoint_digest=parent.checkpoint_digest,
            parent_optimizer_state_digest=parent.optimizer_state_digest,
            parent_rng_state_digest=parent.rng_state_digest,
        )
    elif stage == "final":
        kwargs.update(
            normalized_schedule_progress=1.0,
            replay_evaluation_digest=digest({"replay": size}),
            replay_admissible=bool(replay_ok),
            physical_qualification_passed=bool(physical_ok),
            physical_qualification_digest=digest({"physical": size}),
            parent_checkpoint_digest=parent.checkpoint_digest,
            parent_optimizer_state_digest=parent.optimizer_state_digest,
            parent_rng_state_digest=parent.rng_state_digest,
        )
    return mdstats.TargetSizeTrainingEvidence(**kwargs)


def test_size_halve2_policy_freezes_eight_rungs_and_3_10_30_counts():
    policy = mdstats.SizeHalve2Policy()
    assert policy.target_sizes == (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    assert policy.min_coverage_qualifiers == 4
    assert (policy.coarse_training_epochs, policy.max_coarse_training_candidates) == (3, 4)
    assert (policy.short_training_epochs, policy.max_short_training_candidates) == (10, 2)
    assert policy.final_training_epochs == 30
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.SizeHalve2Policy(target_sizes=SIZES[:-1])


@pytest.mark.parametrize("q", [4, 5, 6, 7, 8])
def test_size_halve2_admits_only_hard_qualified_sizes(q):
    qualified = SIZES[-q:]
    repair, qual = _upstream(qualified=qualified)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    assert plan.outcome == "ready_for_size_fidelity2"
    assert plan.coverage_qualified_sizes == qualified
    assert plan.training_candidate_sizes == qualified
    assert tuple(v.target_size for v in plan.candidates) == SIZES
    assert [v.target_size for v in plan.candidates if v.hard_coverage_qualified] == list(qualified)


def test_size_halve2_blocks_fewer_than_four_qualifiers_without_breaking_legacy_campaign():
    repair, qual = _upstream(qualified=SIZES[-3:])
    plan = mdstats.build_size_halve2_plan(repair, qual)
    assert plan.outcome == "blocked_insufficient_hard_coverage"
    assert plan.training_candidate_sizes == ()
    assert plan.complete


def test_size_halve2_blocks_when_mvqual_nonregression_did_not_pass():
    repair, qual = _upstream(qualified=SIZES, nonregression=False)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    assert plan.outcome == "blocked_mvqual_nonregression"
    assert plan.training_candidate_sizes == ()


def test_epoch3_requires_exactly_qualified_population_and_reduces_q_to_four():
    qualified = SIZES[2:]  # q=6
    repair, qual = _upstream(qualified=qualified)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    evidence = tuple(_ev(size, 10.0 + i, stage="coarse") for i, size in enumerate(qualified))
    with pytest.raises(mdstats.TrainingDataInputError, match="exactly the hard-qualified sizes"):
        mdstats.with_size_halve2_epoch3_evidence(plan, (*evidence, _ev(256, 1.0, stage="coarse")))

    # Boundary is practically tied with the best score and must survive its band.
    scores = {size: 20.0 + i for i, size in enumerate(qualified)}
    scores[qualified[0]] = 5.0
    scores[qualified[-1]] = 5.5
    scores[qualified[1]] = 5.2
    scores[qualified[2]] = 6.4
    scores[qualified[3]] = 7.0
    scores[qualified[4]] = 8.0
    evidence = tuple(_ev(size, scores[size], stage="coarse") for size in qualified)
    plan = mdstats.with_size_halve2_epoch3_evidence(plan, evidence)
    assert plan.outcome == "awaiting_epoch10"
    assert len(plan.stage_b0_survivor_sizes) == 4
    assert qualified[-1] in plan.stage_b0_survivor_sizes
    assert set(plan.stage_b0_survivor_sizes) <= set(qualified)


def test_q4_realizes_four_to_four_then_two_to_one_with_exact_continuation():
    qualified = SIZES[-4:]
    repair, qual = _upstream(qualified=qualified)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    coarse = tuple(_ev(size, float(i + 1), stage="coarse") for i, size in enumerate(qualified))
    plan = mdstats.with_size_halve2_epoch3_evidence(plan, coarse)
    assert set(plan.stage_b0_survivor_sizes) == set(qualified)

    coarse_by = {v.target_size: v for v in plan.coarse_training_evidence}
    short = tuple(_ev(size, float(i + 1), stage="short", parent=coarse_by[size]) for i, size in enumerate(plan.stage_b0_survivor_sizes))
    plan = mdstats.with_size_halve2_epoch10_evidence(plan, short)
    assert plan.outcome == "awaiting_epoch30"
    assert len(plan.stage_b1_finalist_sizes) == 2

    short_by = {v.target_size: v for v in plan.short_training_evidence}
    final_scores = {plan.stage_b1_finalist_sizes[0]: 5.0, plan.stage_b1_finalist_sizes[1]: 5.5}
    final = tuple(_ev(size, final_scores[size], stage="final", parent=short_by[size]) for size in plan.stage_b1_finalist_sizes)
    result = mdstats.with_size_halve2_epoch30_evidence(plan, final)
    assert result.outcome == "selected"
    assert result.selected_target_size == min(plan.stage_b1_finalist_sizes)


def test_epoch10_rejects_restart_instead_of_exact_epoch3_continuation():
    repair, qual = _upstream(qualified=SIZES)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    coarse = tuple(_ev(size, float(i), stage="coarse") for i, size in enumerate(SIZES))
    plan = mdstats.with_size_halve2_epoch3_evidence(plan, coarse)
    coarse_by = {v.target_size: v for v in plan.coarse_training_evidence}
    short = []
    for size in plan.stage_b0_survivor_sizes:
        item = _ev(size, 1.0, stage="short", parent=coarse_by[size])
        short.append(item)
    bad = short[0]
    short[0] = mdstats.TargetSizeTrainingEvidence.from_dict({
        **bad.to_dict(),
        "parent_checkpoint_digest": digest({"wrong": 1}),
        "content_digest": None,
    })
    with pytest.raises(mdstats.TrainingDataInputError, match="continuation ancestry"):
        mdstats.with_size_halve2_epoch10_evidence(plan, tuple(short))


def test_fixed_ceiling_material_improvement_reports_nonconvergence():
    # Arrange early scores so the 16384 boundary remains a finalist.
    repair, qual = _upstream(qualified=SIZES)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    coarse_scores = {size: 20.0 for size in SIZES}
    coarse_scores.update({128: 5.0, 256: 5.1, 512: 5.2, 16384: 5.3})
    coarse = tuple(_ev(size, coarse_scores[size], stage="coarse") for size in SIZES)
    plan = mdstats.with_size_halve2_epoch3_evidence(plan, coarse)
    coarse_by = {v.target_size: v for v in plan.coarse_training_evidence}
    short_scores = {size: (5.0 if size == 128 else 5.1 if size == 16384 else 20.0) for size in plan.stage_b0_survivor_sizes}
    short = tuple(_ev(size, short_scores[size], stage="short", parent=coarse_by[size]) for size in plan.stage_b0_survivor_sizes)
    plan = mdstats.with_size_halve2_epoch10_evidence(plan, short)
    assert 16384 in plan.stage_b1_finalist_sizes
    short_by = {v.target_size: v for v in plan.short_training_evidence}
    final = []
    for size in plan.stage_b1_finalist_sizes:
        score = 1.0 if size == 16384 else 5.0
        final.append(_ev(size, score, stage="final", parent=short_by[size]))
    result = mdstats.with_size_halve2_epoch30_evidence(plan, tuple(final))
    assert result.outcome == "nonconverged_at_fixed_ceiling"


def test_size_halve2_round_trip_and_live_authority_validation():
    repair, qual = _upstream(qualified=SIZES[-6:])
    plan = mdstats.build_size_halve2_plan(repair, qual)
    restored = mdstats.SizeHalve2Plan.from_dict(plan.to_dict())
    assert restored.to_dict() == plan.to_dict()
    mdstats.validate_size_halve2_authority(restored, target_multi_view_repair=repair, target_multi_view_qualification=qual)

def test_size_halve2_perf_p2r_stage_geometry_trains_only_qualified_candidates():
    qualified = SIZES[-6:]
    repair, qual = _upstream(qualified=qualified)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    stage = mdstats.build_size_halve2_execution_stage_plan(plan)
    assert stage.stage == "coarse"
    assert stage.candidate_sizes == qualified
    assert (stage.start_epoch, stage.target_epoch, stage.planned_final_epoch) == (0, 3, 30)

    coarse = tuple(_ev(size, float(i), stage="coarse") for i, size in enumerate(qualified))
    plan = mdstats.with_size_halve2_epoch3_evidence(plan, coarse)
    stage = mdstats.build_size_halve2_execution_stage_plan(plan)
    assert stage.stage == "short"
    assert len(stage.candidate_sizes) == 4
    assert (stage.start_epoch, stage.target_epoch) == (3, 10)
    assert stage.continuation_required

def test_epoch10_requires_same_training_run_identity_and_exact_schedule_progress():
    qualified = SIZES[-4:]
    repair, qual = _upstream(qualified=qualified)
    plan = mdstats.build_size_halve2_plan(repair, qual)
    coarse = tuple(_ev(size, float(i), stage="coarse") for i, size in enumerate(qualified))
    plan = mdstats.with_size_halve2_epoch3_evidence(plan, coarse)
    coarse_by = {v.target_size: v for v in plan.coarse_training_evidence}
    short = [_ev(size, float(i), stage="short", parent=coarse_by[size]) for i, size in enumerate(plan.stage_b0_survivor_sizes)]
    bad = short[0]
    payload = bad.to_dict()
    payload.update(training_run_digest=digest({"different-run": 1}), content_digest=None)
    short[0] = mdstats.TargetSizeTrainingEvidence.from_dict(payload)
    with pytest.raises(mdstats.TrainingDataInputError, match="training run identity changed"):
        mdstats.with_size_halve2_epoch10_evidence(plan, tuple(short))

    short = [_ev(size, float(i), stage="short", parent=coarse_by[size]) for i, size in enumerate(plan.stage_b0_survivor_sizes)]
    bad = short[0]
    payload = bad.to_dict()
    payload.update(normalized_schedule_progress=0.4, content_digest=None)
    short[0] = mdstats.TargetSizeTrainingEvidence.from_dict(payload)
    with pytest.raises(mdstats.TrainingDataInputError, match="exact 10/30"):
        mdstats.with_size_halve2_epoch10_evidence(plan, tuple(short))
