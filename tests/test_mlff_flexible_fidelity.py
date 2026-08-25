from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

import mdstats
from mdstats.training_data._common import TrainingDataInputError, digest


def _h(tag: str) -> str:
    return digest({"tag": tag})


@dataclass(frozen=True)
class _Domain:
    label_domain_id: str
    repaired_master_order: tuple[str, ...]


class _Repair:
    dataset_id = "flexible-fixture"
    content_digest = _h("repair")
    domains = (_Domain("d", tuple(f"u{i}" for i in range(20000))),)

    def domain(self, label_domain_id: str) -> _Domain:
        assert label_domain_id == "d"
        return self.domains[0]


class _Qual:
    dataset_id = _Repair.dataset_id
    target_multi_view_repair_digest = _Repair.content_digest
    mv_qualified_sizes = (512, 1024, 2048)
    content_digest = _h("qual")


def _evidence(plan: object, *, stage: str, epoch: int, size: int, parent: object | None = None):
    kwargs = {
        "stage": stage,
        "target_size": size,
        "optimizer_seed": 1,
        "completed_epochs": epoch,
        "planned_epochs": 40,
        "optimizer_update_count": epoch * 10,
        "structures_presented": epoch * size,
        "normalized_schedule_progress": epoch / 40,
        "instantaneous_learning_rate": 1.0e-3,
        "wall_time_seconds": float(epoch),
        "target_force_score_mev_per_a": float(size),
        "foundation_identity_digest": _h("foundation"),
        "evaluation_role_digest": _h("role"),
        "training_policy_digest": _h("policy"),
        "target_size_study_policy_digest": plan.policy.policy_digest,
        "training_run_digest": _h(f"run-{size}"),
        "candidate_data_digest": plan.candidate(size).candidate_data_digest,
        "checkpoint_digest": _h(f"checkpoint-{size}-{epoch}"),
        "schedule_digest": _h("schedule-40"),
        "optimizer_state_digest": _h(f"optimizer-{size}-{epoch}"),
        "rng_state_digest": _h(f"rng-{size}-{epoch}"),
        "target_evaluation_digest": _h(f"eval-{size}-{epoch}"),
    }
    if parent is not None:
        kwargs.update(
            parent_checkpoint_digest=parent.checkpoint_digest,
            parent_optimizer_state_digest=parent.optimizer_state_digest,
            parent_rng_state_digest=parent.rng_state_digest,
        )
    return mdstats.TargetSizeStudyTrainingEvidence(**kwargs)


def test_nondefault_tuple_uses_semantic_states_and_independent_horizon() -> None:
    policy = mdstats.TargetSizeStudyPolicy(fidelity_epochs=(2, 5, 12), screening_optimizer_seeds=(1,))
    plan = mdstats.build_target_size_study(_Repair(), _Qual(), policy=policy, training_horizon_epochs=40)
    assert plan.outcome == mdstats.OUTCOME_AWAITING_COARSE_SCREEN
    assert (plan.next_training_stage, plan.next_training_epoch) == (mdstats.STAGE_COARSE, 2)
    coarse = tuple(_evidence(plan, stage=mdstats.STAGE_COARSE, epoch=2, size=size) for size in plan.qualified_sizes)
    plan = mdstats.attach_coarse_outcomes(plan, coarse)
    assert (plan.outcome, plan.next_training_epoch) == (mdstats.OUTCOME_AWAITING_SHORT_SCREEN, 5)
    short = tuple(_evidence(plan, stage=mdstats.STAGE_SHORT, epoch=5, size=size, parent=next(item.success for item in plan.coarse_outcomes if item.key == (size, 1))) for size in plan.coarse_survivor_sizes)
    plan = mdstats.attach_short_outcomes(plan, short)
    assert (plan.outcome, plan.next_training_epoch) == (mdstats.OUTCOME_AWAITING_FINAL_SCREEN, 12)
    final = tuple(_evidence(plan, stage=mdstats.STAGE_FINAL_SCREEN, epoch=12, size=size, parent=next(item.success for item in plan.short_outcomes if item.key == (size, 1))) for size in plan.short_finalist_sizes)
    plan = mdstats.attach_final_screen_outcomes(plan, final)
    assert plan.outcome == mdstats.OUTCOME_SELECTED
    stage = mdstats.build_perf_p2r_stage_plan(plan)
    assert (stage.stage, stage.target_epoch, stage.schedule_horizon_epoch) == ("production", 40, 40)


def test_screen_evidence_rejects_wrong_full_horizon() -> None:
    policy = mdstats.TargetSizeStudyPolicy(fidelity_epochs=(2, 5, 12), screening_optimizer_seeds=(1,))
    plan = mdstats.build_target_size_study(_Repair(), _Qual(), policy=policy, training_horizon_epochs=40)
    wrong = _evidence(plan, stage=mdstats.STAGE_COARSE, epoch=2, size=512)
    wrong = replace(wrong, planned_epochs=30, normalized_schedule_progress=2 / 30)
    batch = (wrong,) + tuple(
        _evidence(plan, stage=mdstats.STAGE_COARSE, epoch=2, size=size)
        for size in plan.qualified_sizes if size != 512
    )
    with pytest.raises(TrainingDataInputError, match="schedule horizon"):
        mdstats.attach_coarse_outcomes(plan, batch)


def test_size_fidelity_plan_keeps_final_screen_and_reference_roles_distinct() -> None:
    policy = mdstats.TargetSizeStudyPolicy(fidelity_epochs=(2, 5, 12))
    calibration = mdstats.SizeFidelityCalibrationPolicy(coarse_epoch_candidates=(2, 3, 4))
    plan = mdstats.build_size_fidelity_execution_plan(
        dataset_id="fixture",
        target_size_candidate_authority_digest=_h("candidate-authority"),
        target_size_policy=policy,
        target_sizes=(512, 1024, 2048),
        calibration_policy=calibration,
        training_horizon_epochs=40,
    )
    assert (plan.short_screen_epoch, plan.final_screen_epoch, plan.reference_training_epoch) == (5, 12, 40)
    assert plan.required_checkpoint_epochs == (2, 3, 4, 5, 12, 40)


def test_perf_exposure_uses_incremental_weighted_screen_work_and_full_reference() -> None:
    exposure = mdstats.build_perf_p2r_exposure(
        admissible_sizes=(128, 256, 512),
        coarse_survivor_sizes=(256, 512),
        short_finalist_sizes=(512,),
        coarse_screen_epoch=2,
        short_screen_epoch=5,
        final_screen_epoch=12,
        reference_training_epoch=40,
    )
    assert exposure.total_structure_epochs == 2 * (128 + 256 + 512) + 3 * (256 + 512) + 7 * 512
    assert exposure.exhaustive_structure_epochs == 40 * (128 + 256 + 512)


def test_candidate_materialization_identity_excludes_later_screen_geometry() -> None:
    first = mdstats.build_target_size_study(
        _Repair(), _Qual(),
        policy=mdstats.TargetSizeStudyPolicy(fidelity_epochs=(1, 3, 10)),
        training_horizon_epochs=30,
    )
    second = mdstats.build_target_size_study(
        _Repair(), _Qual(),
        policy=mdstats.TargetSizeStudyPolicy(fidelity_epochs=(2, 5, 12)),
        training_horizon_epochs=40,
    )
    assert first.policy.policy_digest != second.policy.policy_digest
    assert first.candidate_authority_digest == second.candidate_authority_digest


def test_preparation_config_identity_excludes_only_downstream_fidelity_controls() -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    base = {
        "schema": "mdstats.mlff-campaign-cli.v2",
        "target_data": {"size_convergence": {
            "fidelity_epochs": [1, 3, 10],
            "coarse_practical_equivalence_mev_per_a": 1.0,
            "practical_equivalence_mev_per_a": 1.0,
            "coverage_threshold": 0.95,
        }},
        "training": {"modes": ["multihead_replay"], "seeds": [1, 2]},
    }
    changed_fidelity = {
        **base,
        "target_data": {"size_convergence": {
            **base["target_data"]["size_convergence"], "fidelity_epochs": [2, 5, 12],
        }},
    }
    changed_preparation = {
        **base,
        "target_data": {"size_convergence": {
            **base["target_data"]["size_convergence"], "coverage_threshold": 0.90,
        }},
    }
    assert cli._preparation_config_digest(base) == cli._preparation_config_digest(changed_fidelity)
    assert cli._preparation_config_digest(base) != cli._preparation_config_digest(changed_preparation)


def test_authenticated_fixed_generation_plan_migrates_without_new_default_substitution() -> None:
    old_policy = {
        "schema": "mdstats.target-size-study-policy.v6",
        "authority_version": "mdstats.target-size-study.fixed-eight.2026-08.v5.3",
        "candidate_sizes": list(mdstats.FIXED_TARGET_SIZES),
        "minimum_qualified_sizes": 3,
        "epoch3_survivor_limit": 4,
        "epoch10_finalist_count": 2,
        "fidelity_epochs": [3, 10, 30],
        "practical_equivalence_mev_per_a": 1.0,
        "coarse_practical_equivalence_mev_per_a": 1.0,
        "screening_optimizer_seeds": [1],
        "paired_seed_aggregation": "arithmetic_mean",
    }
    old_policy["policy_digest"] = digest(old_policy)
    current = mdstats.build_target_size_study(
        _Repair(), _Qual(), policy=mdstats.TargetSizeStudyPolicy(fidelity_epochs=(3, 10, 30), screening_optimizer_seeds=(1,))
    )
    legacy = {
        "schema": "mdstats.target-size-study-plan.v8",
        "authority_version": "mdstats.target-size-study.fixed-eight.2026-08.v5.3",
        "dataset_id": current.dataset_id,
        "repair2_authority_digest": current.repair2_authority_digest,
        "mvqual_authority_digest": current.mvqual_authority_digest,
        "policy": old_policy,
        "candidates": [item.to_dict() for item in current.candidates],
        "qualified_sizes": list(current.qualified_sizes),
        "epoch3_outcomes": [], "epoch3_survivor_sizes": [],
        "epoch10_outcomes": [], "epoch10_finalist_sizes": [], "epoch30_outcomes": [],
        "selected_target_size": None,
        "outcome": "awaiting_epoch_3",
        "decision_reason": "legacy fixture",
        "comparison_failure_stage": None,
        "comparison_failures": [],
    }
    legacy["content_digest"] = digest(legacy)
    migrated = mdstats.TargetSizeStudyPlan.from_dict(legacy)
    assert migrated.policy.fidelity_epochs == (3, 10, 30)
    assert migrated.outcome == mdstats.OUTCOME_AWAITING_COARSE_SCREEN
    legacy["qualified_sizes"] = [512]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        mdstats.TargetSizeStudyPlan.from_dict(legacy)
