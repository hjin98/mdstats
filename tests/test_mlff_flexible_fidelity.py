from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

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


def _evidence(
    plan: object,
    *,
    stage: str,
    epoch: int,
    size: int,
    planned_epochs: int = 40,
    target_score: float | None = None,
    parent: object | None = None,
):
    planned_epochs = int(planned_epochs)
    kwargs = {
        "stage": stage,
        "target_size": size,
        "optimizer_seed": 1,
        "completed_epochs": epoch,
        "planned_epochs": planned_epochs,
        "optimizer_update_count": epoch * 10,
        "structures_presented": epoch * size,
        "normalized_schedule_progress": epoch / planned_epochs,
        "instantaneous_learning_rate": 1.0e-3,
        "wall_time_seconds": float(epoch),
        "target_force_score_mev_per_a": float(size if target_score is None else target_score),
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


def _complete_funnel(
    *,
    fidelity_epochs: tuple[int, int, int],
    training_horizon: int,
    qualified_sizes: tuple[int, ...] = (512, 1024, 2048),
    coarse_scores: dict[int, float] | None = None,
    short_scores: dict[int, float] | None = None,
    final_scores: dict[int, float] | None = None,
):
    policy = mdstats.TargetSizeStudyPolicy(
        fidelity_epochs=fidelity_epochs,
        screening_optimizer_seeds=(1,),
    )
    repair = _Repair()
    qualification = SimpleNamespace(
        dataset_id=repair.dataset_id,
        target_multi_view_repair_digest=repair.content_digest,
        mv_qualified_sizes=qualified_sizes,
        content_digest=_h(f"qual-{fidelity_epochs}-{qualified_sizes}"),
    )
    plan = mdstats.build_target_size_study(
        repair,
        qualification,
        policy=policy,
        training_horizon_epochs=training_horizon,
    )
    coarse_scores = coarse_scores or {size: float(size) for size in plan.qualified_sizes}
    coarse = tuple(
        _evidence(
            plan,
            stage=mdstats.STAGE_COARSE,
            epoch=fidelity_epochs[0],
            size=size,
            planned_epochs=training_horizon,
            target_score=coarse_scores[size],
        )
        for size in plan.qualified_sizes
    )
    plan = mdstats.attach_coarse_outcomes(plan, coarse)
    short_scores = short_scores or {size: float(size) for size in plan.coarse_survivor_sizes}
    short = tuple(
        _evidence(
            plan,
            stage=mdstats.STAGE_SHORT,
            epoch=fidelity_epochs[1],
            size=size,
            planned_epochs=training_horizon,
            target_score=short_scores[size],
            parent=next(item.success for item in plan.coarse_outcomes if item.key == (size, 1)),
        )
        for size in plan.coarse_survivor_sizes
    )
    plan = mdstats.attach_short_outcomes(plan, short)
    final_scores = final_scores or {size: float(size) for size in plan.short_finalist_sizes}
    final = tuple(
        _evidence(
            plan,
            stage=mdstats.STAGE_FINAL_SCREEN,
            epoch=fidelity_epochs[2],
            size=size,
            planned_epochs=training_horizon,
            target_score=final_scores[size],
            parent=next(item.success for item in plan.short_outcomes if item.key == (size, 1)),
        )
        for size in plan.short_finalist_sizes
    )
    return mdstats.attach_final_screen_outcomes(plan, final)


def _persistable_target_size_authorities() -> tuple[object, object]:
    """Return compact, fully serializable REPAIR2/MVQUAL2 input authorities.

    The campaign integration tests deliberately persist these real records
    instead of replacing the target-size owner with a helper double.  The
    fixtures model only the already-qualified prefix universe; they do not
    stand in for any target-size reduction or restart behavior.
    """

    from mdstats.training_data._target_multi_view_scoring import (
        TargetMultiViewSelectorTelemetry,
    )
    from mdstats.training_data.target_multi_view_repair import TargetMultiViewRepairRung
    from mdstats.training_data.target_multi_view_repair_v2 import (
        TargetMultiViewRepairDomainPlanV2,
        TargetMultiViewRepairPlanV2,
        TargetMultiViewRepairPolicyV2,
    )
    from mdstats.training_data.target_multi_view_qualification_v2 import (
        OUTCOME_QUALIFIED,
        TargetMultiViewQualificationDomainPlanV2,
        TargetMultiViewQualificationPlanV2,
        TargetMultiViewQualificationPolicyV2,
        TargetMultiViewQualificationRungV2,
    )

    uids = tuple(_h(f"persisted-frame-{index}") for index in range(16_384))
    repair_domain = TargetMultiViewRepairDomainPlanV2(
        label_domain_id="target",
        reference_domain_digest=_h("persisted-reference-domain"),
        mvidx1_domain_digest=_h("persisted-sparse-domain"),
        selection_domain_digest=_h("persisted-selection-domain"),
        candidate_count=len(uids),
        repaired_master_order=uids,
        rungs=tuple(
            TargetMultiViewRepairRung(
                target_size=size,
                materializable=True,
                active_shell_start=0,
                frame_uids=uids[:size],
                hard_obligations_passed=True,
                hard_coverage_qualified=True,
            )
            for size in mdstats.FIXED_TARGET_SIZES
        ),
        total_swaps=0,
    )
    repair = TargetMultiViewRepairPlanV2(
        dataset_id="persisted-flexible-fixture",
        target_coverage_reference_digest=_h("persisted-reference"),
        mvidx1_content_digest=_h("persisted-sparse-index"),
        target_multi_view_selection_v2_digest=_h("persisted-selection"),
        policy=TargetMultiViewRepairPolicyV2(),
        domains=(repair_domain,),
    )
    telemetry = TargetMultiViewSelectorTelemetry(
        uncovered_witness_count=0,
        uncovered_reference_mass=0.0,
        unique_reference_mass_fraction=0.1,
        zero_unique_candidate_fraction=0.0,
        correlation_unit_count=1,
        maximum_correlation_unit_fraction=1.0,
        run_count=1,
        condition_count=1,
    )
    qualification_domain = TargetMultiViewQualificationDomainPlanV2(
        label_domain_id="target",
        reference_domain_digest=repair_domain.reference_domain_digest,
        sparse_domain_digest=repair_domain.mvidx1_domain_digest,
        repair_domain_digest=repair_domain.content_digest,
        rungs=tuple(
            TargetMultiViewQualificationRungV2(
                target_size=size,
                materializable=True,
                coverage_passed=True,
                hard_obligations_passed=True,
                qualified=True,
                coverage_report_digest=_h(f"persisted-coverage-{size}"),
                telemetry=telemetry,
            )
            for size in mdstats.FIXED_TARGET_SIZES
        ),
    )
    qualification = TargetMultiViewQualificationPlanV2(
        dataset_id=repair.dataset_id,
        target_coverage_reference_digest=repair.target_coverage_reference_digest,
        target_coverage_sparse_index_digest=repair.mvidx1_content_digest,
        target_coverage_feasibility_digest=_h("persisted-feasibility"),
        target_data_role_freeze_digest=_h("persisted-role-freeze"),
        target_multi_view_repair_digest=repair.content_digest,
        policy=TargetMultiViewQualificationPolicyV2(),
        domains=(qualification_domain,),
        mv_qualified_sizes=mdstats.FIXED_TARGET_SIZES,
        outcome=OUTCOME_QUALIFIED,
    )
    return repair, qualification


def _attach_persisted_boundary_evidence(plan: object) -> object:
    """Perform one real semantic reduction for the active persisted study."""

    stage = plan.next_training_stage
    epoch = int(plan.next_training_epoch)
    sizes = tuple(int(value) for value in plan.next_training_sizes)
    previous = {
        (item.success.target_size, item.success.optimizer_seed): item.success
        for item in (*plan.coarse_outcomes, *plan.short_outcomes)
        if item.success is not None
    }
    outcomes = []
    for size in sizes:
        for seed in plan.policy.screening_optimizer_seeds:
            item = _evidence(
                plan,
                stage=stage,
                epoch=epoch,
                size=size,
                planned_epochs=plan.training_horizon_epochs,
                target_score=float(size),
                parent=previous.get((size, seed)),
            )
            outcomes.append(
                replace(
                    item,
                    optimizer_seed=seed,
                    training_run_digest=_h(f"persisted-run-{size}-{seed}"),
                    checkpoint_digest=_h(f"persisted-checkpoint-{size}-{seed}-{epoch}"),
                    optimizer_state_digest=_h(f"persisted-optimizer-{size}-{seed}-{epoch}"),
                    rng_state_digest=_h(f"persisted-rng-{size}-{seed}-{epoch}"),
                    target_evaluation_digest=_h(f"persisted-evaluation-{size}-{seed}-{epoch}"),
                )
            )
    if stage == mdstats.STAGE_COARSE:
        return mdstats.attach_coarse_outcomes(plan, tuple(outcomes))
    if stage == mdstats.STAGE_SHORT:
        return mdstats.attach_short_outcomes(plan, tuple(outcomes))
    assert stage == mdstats.STAGE_FINAL_SCREEN
    return mdstats.attach_final_screen_outcomes(plan, tuple(outcomes))


def test_supplemental_case_a_default_funnel_reaches_production_and_roundtrips_status() -> None:
    plan = _complete_funnel(fidelity_epochs=(1, 3, 10), training_horizon=30)
    assert plan.outcome == mdstats.OUTCOME_SELECTED
    assert plan.policy.fidelity_epochs == (1, 3, 10)
    assert mdstats.TargetSizeStudyPlan.from_dict(plan.to_dict()) == plan
    production = mdstats.build_perf_p2r_stage_plan(plan)
    assert (
        production.stage,
        production.target_epoch,
        production.schedule_horizon_epoch,
    ) == ("production", 30, 30)


def test_supplemental_case_b_nondefault_funnel_authenticates_full_horizon_and_denominators() -> None:
    plan = _complete_funnel(
        fidelity_epochs=(2, 5, 12),
        training_horizon=40,
        qualified_sizes=(512, 1024, 2048, 4096, 8192),
        coarse_scores={512: 50.0, 1024: 40.0, 2048: 30.0, 4096: 20.0, 8192: 10.0},
        short_scores={1024: 14.0, 2048: 12.0, 4096: 10.0, 8192: 8.0},
        final_scores={4096: 6.0, 8192: 5.0},
    )
    assert plan.outcome == mdstats.OUTCOME_SELECTED
    assert 512 not in plan.coarse_survivor_sizes
    assert len(plan.short_finalist_sizes) == 2
    production = mdstats.build_perf_p2r_stage_plan(plan)
    assert (
        production.target_epoch,
        production.schedule_horizon_epoch,
        production.candidate_sizes,
    ) == (40, 40, (plan.selected_target_size,))
    exposure = mdstats.build_perf_p2r_exposure(
        plan.qualified_sizes,
        plan.coarse_survivor_sizes,
        plan.short_finalist_sizes,
        coarse_screen_epoch=2,
        short_screen_epoch=5,
        final_screen_epoch=12,
        reference_training_epoch=40,
    )
    assert exposure.exhaustive_structure_epochs == 40 * sum(plan.qualified_sizes)
    assert exposure.total_structure_epochs < exposure.exhaustive_structure_epochs
    assert plan.next_training_stage is None
    assert mdstats.TargetSizeStudyPlan.from_dict(plan.to_dict()).selected_target_size == plan.selected_target_size


def test_supplemental_case_c_deduplicates_physical_final_reference_endpoint_but_keeps_roles() -> None:
    policy = mdstats.TargetSizeStudyPolicy(
        fidelity_epochs=(1, 3, 30),
        screening_optimizer_seeds=(1,),
    )
    calibration = mdstats.SizeFidelityCalibrationPolicy(coarse_epoch_candidates=(1,))
    execution = mdstats.build_size_fidelity_execution_plan(
        dataset_id="case-c",
        target_size_candidate_authority_digest=_h("case-c-authority"),
        target_size_policy=policy,
        target_sizes=(512, 1024, 2048),
        calibration_policy=calibration,
        training_horizon_epochs=30,
    )
    assert execution.final_screen_epoch == 30
    assert execution.reference_training_epoch == 30
    assert execution.required_checkpoint_epochs == (1, 3, 30)
    assert execution.expected_checkpoint_count == execution.expected_training_run_count * 3


@pytest.mark.parametrize(
    ("fidelity_epochs", "horizon"),
    [((1, 3, 10), 30), ((2, 5, 12), 40)],
)
def test_supplemental_persisted_campaign_selects_configured_boundaries_and_exposes_restart_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    fidelity_epochs: tuple[int, int, int],
    horizon: int,
) -> None:
    """Exercise config, SQLite, target-size ownership, reductions, and status.

    MACE training/evaluation are intentionally replaced at their external
    execution boundary.  Configuration normalization, CampaignStore,
    TARGET-SIZE-V5 construction/validation, evidence reduction, selected-size
    persistence, status, and restart lifecycle derivation remain real.
    """

    from mdstats.training_data import _campaign_cli_core as cli

    config = tmp_path / "campaign.toml"
    config.write_text(
        cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay-train.xyz",
            replay_monitor="replay-monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    text = config.read_text(encoding="utf-8")
    text = text.replace(
        "fidelity_epochs = [1, 3, 10]",
        f"fidelity_epochs = {list(fidelity_epochs)}",
    ).replace("max_num_epochs = 30", f"max_num_epochs = {horizon}", 1)
    config.write_text(text, encoding="utf-8")
    cfg, paths = cli._load_config(config)
    paths.ensure()
    store = cli.CampaignStore(paths.state_db)
    repair, qualification = _persistable_target_size_authorities()
    store.put_records(
        {
            "target_multi_view_repair_v2": repair,
            "target_multi_view_qualification_v2": qualification,
        }
    )
    cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture doctor passed")
    frozen = cli._ensure_target_size_study(
        store, cfg=cfg, repair2=repair, mvqual2=qualification
    )
    assert (frozen.policy.fidelity_epochs, frozen.training_horizon_epochs) == (
        fidelity_epochs,
        horizon,
    )
    assert cli._load_verified_target_size_study_authority(store).content_digest == frozen.content_digest

    authorized_boundaries: list[int] = []

    def fake_train(_args: argparse.Namespace) -> int:
        study = cli._load_verified_target_size_study_authority(store)
        authorized_boundaries.append(int(study.next_training_epoch))
        cli._mark_stage(store, paths, "train", cli.StageState.COMPLETE, "external bounded train passed")
        return 0

    def fake_evaluate(_args: argparse.Namespace) -> int:
        study = cli._load_verified_target_size_study_authority(store)
        store.put_record("target_size_study", _attach_persisted_boundary_evidence(study))
        cli._mark_stage(store, paths, "evaluate", cli.StageState.COMPLETE, "external endpoint evaluation passed")
        return 0

    # The fixture has no physical DATA8 tree.  The actual selection owner and
    # all persisted semantic state stay intact; only the unavailable MACE smoke
    # transport is admitted as an external-compute substitute.
    monkeypatch.setattr(cli, "_require_train2_preflight_authorization", lambda *_args: ([], "fixture"))
    monkeypatch.setattr(cli, "_execute_train_current_authority", fake_train)
    monkeypatch.setattr(cli, "_execute_evaluate_current_authority", fake_evaluate)

    assert cli.command_select_target_size(argparse.Namespace(config=str(config))) == 0
    selection_output = capsys.readouterr().out
    assert f"fidelity_epochs={list(fidelity_epochs)}" in selection_output
    assert f"schedule_horizon={horizon}" in selection_output
    assert f"screen_boundary={fidelity_epochs[0]}" in selection_output
    selected = cli._load_verified_target_size_study_authority(store)
    assert selected.outcome == mdstats.OUTCOME_SELECTED
    assert authorized_boundaries == list(fidelity_epochs)
    assert mdstats.build_perf_p2r_stage_plan(selected).schedule_horizon_epoch == horizon

    # Reopen the durable store to prove that a restart/status consumer sees the
    # frozen selection rather than helper-local state.
    store.close()
    reopened = cli.CampaignStore(paths.state_db)
    assert cli._next_public_operation(cfg, paths, reopened) == "materialize"
    assert cli.command_status(argparse.Namespace(config=str(config))) == 0
    status = capsys.readouterr().out
    assert f"selected target size frozen at n={selected.selected_target_size}" in status
    assert "Next command:" in status and " materialize" in status
    reopened.close()


@pytest.mark.parametrize(
    ("replacement", "horizon", "expected_epoch", "reason"),
    (
        ((2, 3, 10), 30, 2, "fidelity"),
        ((1, 5, 10), 30, 1, "fidelity"),
        ((1, 3, 12), 30, 1, "fidelity"),
        ((1, 3, 10), 40, 1, "horizon"),
    ),
)
def test_real_campaign_store_frontier_replaces_only_target_size_and_live_train2_state(
    tmp_path: Path,
    replacement: tuple[int, int, int],
    horizon: int,
    expected_epoch: int,
    reason: str,
) -> None:
    """Exercise durable study replacement and forensic TRAIN2 invalidation.

    This fixture intentionally constructs only the already-qualified REPAIR2/
    MVQUAL2 authorities and compact live downstream state.  The current TOML
    parser, SQLite `CampaignStore`, target-size construction/serialization,
    stage markers, and invalidation owner all remain real.
    """

    from mdstats.training_data import _campaign_cli_core as cli

    config = tmp_path / "campaign.toml"
    config.write_text(
        cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay-train.xyz",
            replay_monitor="replay-monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    cfg, paths = cli._load_config(config)
    paths.ensure()
    repair, qualification = _persistable_target_size_authorities()
    store = cli.CampaignStore(paths.state_db)
    store.put_records(
        {
            "target_multi_view_repair_v2": repair,
            "target_multi_view_qualification_v2": qualification,
            # These compact payloads model persisted scientific products and
            # are deliberately not TRAIN2 invalidation targets.
            "data7:fixture": {"schema": "fixture.data7", "content_digest": _h("data7")},
            "data8:fixture": {"schema": "fixture.data8", "content_digest": _h("data8")},
            "execution:old": {"schema": "fixture.execution", "content_digest": _h("execution")},
            "training_campaign": {"schema": "fixture.campaign", "content_digest": _h("campaign")},
        }
    )
    previous = cli._ensure_target_size_study(
        store, cfg=cfg, repair2=repair, mvqual2=qualification
    )
    cli._mark_stage(store, paths, "prepare", cli.StageState.COMPLETE, "fixture prepare")
    cli._mark_stage(store, paths, "preflight", cli.StageState.COMPLETE, "fixture preflight")
    store.close()

    text = config.read_text(encoding="utf-8")
    text = text.replace("fidelity_epochs = [1, 3, 10]", f"fidelity_epochs = {list(replacement)}")
    text = text.replace("max_num_epochs = 30", f"max_num_epochs = {horizon}", 1)
    config.write_text(text, encoding="utf-8")
    changed_cfg, changed_paths = cli._load_config(config)
    reopened = cli.CampaignStore(changed_paths.state_db)
    current_repair = reopened.get_record("target_multi_view_repair_v2", type(repair))
    current_qualification = reopened.get_record(
        "target_multi_view_qualification_v2", type(qualification)
    )
    fresh = cli._ensure_target_size_study(
        reopened, cfg=changed_cfg, repair2=current_repair, mvqual2=current_qualification
    )

    assert fresh.content_digest != previous.content_digest
    assert fresh.policy.fidelity_epochs == replacement
    assert fresh.training_horizon_epochs == horizon
    assert fresh.next_training_epoch == expected_epoch
    assert reopened.has_record("data7:fixture")
    assert reopened.has_record("data8:fixture")

    cli._invalidate_train2_downstream_state(
        reopened,
        changed_paths,
        reason=f"fixture {reason} transition",
        preserve_preflight=True,
    )
    assert not reopened.has_record("execution:old")
    assert not reopened.has_record("training_campaign")
    assert any(
        key.startswith("historical:train2-invalidation:execution:old:")
        for key in reopened.record_keys("historical:train2-invalidation:")
    )
    assert reopened.stage("prepare")[0] is cli.StageState.COMPLETE
    assert reopened.stage("preflight")[0] is cli.StageState.COMPLETE
    for stage in ("train", "evaluate", "verify"):
        assert reopened.stage(stage) == (cli.StageState.WAITING, f"fixture {reason} transition")
    reopened.close()


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
        "campaign": {"id": "campaign-a", "workspace": "work-a", "profile": "lta"},
        "target_data": {"size_convergence": {
            "fidelity_epochs": [1, 3, 10],
            "coarse_practical_equivalence_mev_per_a": 1.0,
            "practical_equivalence_mev_per_a": 1.0,
            "coverage_threshold": 0.95,
        }},
        "training": {
            "policy_generation": "train2",
            "modes": ["multihead_replay"],
            "seeds": [1, 2],
            "max_num_epochs": 30,
        },
        "evaluation": {"finalist_count": 5},
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

    changed_horizon = {
        **base,
        "training": {**base["training"], "max_num_epochs": 40},
    }
    changed_presentation = {
        **base,
        "campaign": {**base["campaign"], "id": "campaign-b", "workspace": "work-b"},
        "evaluation": {"finalist_count": 99},
    }
    assert cli._preparation_config_digest(base) == cli._preparation_config_digest(changed_horizon)
    assert cli._preparation_config_digest(base) == cli._preparation_config_digest(changed_presentation)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("training_backend", "cueq"),
        ("only_cueq", True),
        ("require_available", False),
    ),
)
def test_preparation_identity_excludes_train2_and_acceleration_availability_controls(
    field: str, replacement: object
) -> None:
    """Source inference backend remains semantic; TRAIN2/runtime controls do not."""

    from mdstats.training_data import _campaign_cli_core as cli

    acceleration = {
        "backend": "e3nn",
        "training_backend": "e3nn",
        "only_cueq": False,
        "require_available": True,
    }
    base = {
        "acceleration": acceleration,
        "training": {"policy_generation": "train2", "max_num_epochs": 30},
    }
    changed = {**base, "acceleration": {**acceleration, field: replacement}}
    source_backend_changed = {
        **base,
        "acceleration": {**acceleration, "backend": "cueq"},
    }

    assert cli._preparation_config_digest(base) == cli._preparation_config_digest(changed)
    assert cli._preparation_config_digest(base) != cli._preparation_config_digest(source_backend_changed)


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("max_num_epochs = 30", "max_num_epochs = 40"),
        ("fidelity_epochs = [1, 3, 10]", "fidelity_epochs = [2, 5, 12]"),
        ('training_backend = "cueq"', 'training_backend = "e3nn"'),
        ("only_cueq = false", "only_cueq = true"),
        ("require_available = true", "require_available = false"),
        ('id = "lta-mh1-omat-pbe-finetune"', 'id = "presentation-only-name"'),
    ),
)
def test_real_store_prepare_marker_reuses_execution_only_toml_changes(
    tmp_path: Path, old: str, new: str
) -> None:
    """Stage reuse follows the persisted positive preparation projection."""

    from mdstats.training_data import _campaign_cli_core as cli

    config = tmp_path / "campaign.toml"
    config.write_text(
        cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay-train.xyz",
            replay_monitor="replay-monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _cfg, paths = cli._load_config(config)
    paths.ensure()
    store = cli.CampaignStore(paths.state_db)
    cli._mark_stage(store, paths, "prepare", cli.StageState.COMPLETE, "fixture prepare")
    store.close()

    text = config.read_text(encoding="utf-8")
    assert old in text
    config.write_text(text.replace(old, new, 1), encoding="utf-8")
    _changed_cfg, changed_paths = cli._load_config(config)
    reopened = cli.CampaignStore(changed_paths.state_db)
    assert cli._effective_stage(reopened, changed_paths, "prepare") == (
        cli.StageState.COMPLETE,
        "fixture prepare",
    )
    reopened.close()


def test_real_store_prepare_marker_fails_closed_for_preparation_scientific_change(
    tmp_path: Path,
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    config = tmp_path / "campaign.toml"
    config.write_text(
        cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay-train.xyz",
            replay_monitor="replay-monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _cfg, paths = cli._load_config(config)
    paths.ensure()
    store = cli.CampaignStore(paths.state_db)
    cli._mark_stage(store, paths, "prepare", cli.StageState.COMPLETE, "fixture prepare")
    store.close()

    text = config.read_text(encoding="utf-8")
    assert 'head = "omat_pbe"' in text
    config.write_text(text.replace('head = "omat_pbe"', 'head = "changed-head"', 1), encoding="utf-8")
    _changed_cfg, changed_paths = cli._load_config(config)
    reopened = cli.CampaignStore(changed_paths.state_db)
    state, message = cli._effective_stage(reopened, changed_paths, "prepare")
    assert state is cli.StageState.WAITING
    assert "campaign.toml changed" in message
    reopened.close()


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("max_new_frames", 128),
        ("inference_batch_size", 4),
        ("maximum_inference_batch_size", 32),
        ("estimated_inference_memory_mib_per_frame", 768.0),
        ("batch_calibration_stress_structures", 16),
        ("vram_max_device_fraction", 0.75),
        ("vram_reserve_gib", 6.0),
        ("batch_throughput_tolerance_fraction", 0.10),
        ("pipeline_enabled", False),
        ("persistence_queue_depth", 2),
        ("checkpoint_interval", 256),
        ("artifact_shard_size", 256),
    ),
)
def test_preparation_identity_excludes_execution_only_model_realization_controls(
    field: str, replacement: object
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    model = {
        "device": "cuda",
        "dtype": "float32",
        "max_new_frames": 0,
        "inference_batch_size": 0,
        "maximum_inference_batch_size": 16,
        "estimated_inference_memory_mib_per_frame": 512.0,
        "batch_calibration_stress_structures": 8,
        "vram_max_device_fraction": 0.80,
        "vram_reserve_gib": 4.0,
        "batch_throughput_tolerance_fraction": 0.05,
        "pipeline_enabled": True,
        "persistence_queue_depth": 1,
        "checkpoint_interval": 128,
        "artifact_shard_size": 128,
    }
    base = {
        "model": model,
        "training": {"policy_generation": "train2", "max_num_epochs": 30},
        "target_data": {"size_convergence": {"fidelity_epochs": [1, 3, 10]}},
    }
    changed = {**base, "model": {**model, field: replacement}}

    assert cli._preparation_config_digest(base) == cli._preparation_config_digest(changed)


def test_preflight_matrix_identity_excludes_generated_train2_schedule_files() -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    artifact = type(
        "Artifact",
        (),
        {
            "tree_entries": (
                ("jobs/job/target_train.xyz", _h("target")),
                ("jobs/job/target_valid.xyz", _h("valid")),
                ("jobs/job/mace_config.yaml", _h("horizon-30")),
                ("jobs/job/run_mace.sh", _h("command-30")),
                ("data8_preparation_bundle.json", _h("bundle-30")),
            )
        },
    )()
    materialization = type(
        "Materialization",
        (),
        {"checkpoint": type("Checkpoint", (), {"data8_artifact": artifact})()},
    )()
    first = type(
        "Entry",
        (),
        {
            "variant_id": "multihead_replay-n512-seed1",
            "bundle": type("Bundle", (), {"content_digest": _h("bundle-30")})(),
            "materialization": materialization,
        },
    )()
    second_artifact = type(
        "Artifact",
        (),
        {
            "tree_entries": (
                ("jobs/job/target_train.xyz", _h("target")),
                ("jobs/job/target_valid.xyz", _h("valid")),
                ("jobs/job/mace_config.yaml", _h("horizon-40")),
                ("jobs/job/run_mace.sh", _h("command-40")),
                ("data8_preparation_bundle.json", _h("bundle-40")),
            )
        },
    )()
    second = type(
        "Entry",
        (),
        {
            "variant_id": first.variant_id,
            "bundle": type("Bundle", (), {"content_digest": _h("bundle-40")})(),
            "materialization": type(
                "Materialization",
                (),
                {"checkpoint": type("Checkpoint", (), {"data8_artifact": second_artifact})()},
            )(),
        },
    )()
    assert cli._data8_matrix_digest([first]) == cli._data8_matrix_digest([second])


def test_validated_fidelity_upgrade_reauthenticates_historical_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    paths = SimpleNamespace(config=tmp_path / "campaign.toml")
    entry = SimpleNamespace(variant_id="candidate")
    smoke = {"passed": True, "data8_matrix_digest": _h("legacy-matrix")}

    class Store:
        def __init__(self) -> None:
            self.meta: dict[str, object] = {}
            self.records = {"preflight_smoke": smoke}

        def stage(self, name):
            assert name == "preflight"
            return cli.StageState.COMPLETE, "historical smoke"

        def get_payload_optional(self, key):
            return self.records.get(key)

        def put_record(self, key, payload):
            self.records[key] = payload

        def set_meta(self, key, value):
            self.meta[key] = value

    store = Store()
    monkeypatch.setattr(cli, "_data8_matrix_digest", lambda _entries: _h("semantic-matrix"))
    monkeypatch.setattr(cli, "_legacy_data8_matrix_digest", lambda _entries: _h("legacy-matrix"))
    monkeypatch.setattr(cli, "_stage_config_digest", lambda _paths, name: f"current-{name}")

    assert cli._reconcile_reused_preflight_identity(store, paths, [entry])
    assert store.records["preflight_smoke"]["data8_matrix_digest"] == _h("semantic-matrix")
    assert store.meta["stage_config_sha256:preflight"] == "current-preflight"


def test_reused_preflight_identity_fails_closed_for_unvalidated_smoke(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    paths = SimpleNamespace(config=tmp_path / "campaign.toml")

    class Store:
        def stage(self, name):
            assert name == "preflight"
            return cli.StageState.COMPLETE, "historical smoke"

        def get_payload_optional(self, key):
            assert key == "preflight_smoke"
            return {"passed": False, "data8_matrix_digest": _h("matrix")}

    monkeypatch.setattr(cli, "_data8_matrix_digest", lambda _entries: _h("matrix"))
    assert not cli._reconcile_reused_preflight_identity(store=Store(), paths=paths, entries=[])


def test_train2_frontier_invalidation_preserves_forensic_state_and_resets_live_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    paths = SimpleNamespace(config=tmp_path / "campaign.toml")

    class Store:
        def __init__(self) -> None:
            self.records = {
                "execution:run": {"schema": "execution", "run": "old"},
                "training_campaign": {"schema": "campaign", "run": "old"},
                "unrelated": {"schema": "keep"},
            }
            self.stages: dict[str, tuple[cli.StageState, str]] = {}
            self.meta: dict[str, object] = {}

        def record_keys(self, prefix=""):
            return tuple(sorted(key for key in self.records if key.startswith(prefix)))

        def get_payload_optional(self, key):
            return self.records.get(key)

        def put_record(self, key, payload):
            self.records[key] = payload

        def record_digest(self, key):
            return _h(f"record:{key}")

        def delete_record(self, key):
            self.records.pop(key, None)

        def set_stage(self, name, state, message):
            self.stages[name] = (state, message)

        def set_meta(self, key, value):
            self.meta[key] = value

    store = Store()
    monkeypatch.setattr(cli, "_stage_config_digest", lambda _paths, name: f"digest-{name}")
    cli._invalidate_train2_downstream_state(
        store,
        paths,
        reason="changed horizon",
        preserve_preflight=True,
    )

    assert "execution:run" not in store.records
    assert "training_campaign" not in store.records
    assert "unrelated" in store.records
    assert any(key.startswith("historical:train2-invalidation:execution:run:") for key in store.records)
    assert store.stages == {
        "train": (cli.StageState.WAITING, "changed horizon"),
        "evaluate": (cli.StageState.WAITING, "changed horizon"),
        "verify": (cli.StageState.WAITING, "changed horizon"),
    }


def test_train2_schedule_identity_rejects_cross_horizon_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    budget = type("Policy", (), {"policy_digest": _h("budget-40"), "planned_epochs": 40})()
    lr = type("Policy", (), {"policy_digest": _h("lr")})()
    admissibility = type("Policy", (), {"policy_digest": _h("admissibility")})()
    selection = type("Policy", (), {"policy_digest": _h("selection")})()
    monkeypatch.setattr(
        cli,
        "_train2_policy_set",
        lambda _cfg, *, require_replay: (budget, lr, admissibility, selection),
    )
    protocol = type(
        "Protocol",
        (),
        {
            "training_mode": type("Mode", (), {"value": "multihead_replay"})(),
            "optimizer_policy": type("Optimizer", (), {"max_num_epochs": 30})(),
            "training_budget_policy": type("Policy", (), {"policy_digest": _h("budget-30")})(),
            "learning_rate_schedule_policy": lr,
            "checkpoint_admissibility_policy": admissibility,
            "checkpoint_selection_policy": selection,
        },
    )()
    entry = type(
        "Entry",
        (),
        {"bundle": type("Bundle", (), {"jobs": (type("Job", (), {"protocol": protocol})(),)})()},
    )()
    assert not cli._train2_data8_schedule_matches_config(
        {"training": {"policy_generation": "train2"}}, [entry]
    )


def _migration_cfg(fidelity_epochs: tuple[int, int, int], horizon: int) -> dict:
    return {
        "target_data": {"size_convergence": {"fidelity_epochs": list(fidelity_epochs)}},
        "training": {
            "policy_generation": "train2",
            "modes": ["multihead_replay"],
            "seeds": [1],
            "device": "cpu",
            "dtype": "float32",
            "max_num_epochs": horizon,
            "learning_rate": 1.0e-4,
            "batch_size": 2,
            "valid_batch_size": 2,
            "num_workers": 0,
        },
        "model": {"dtype": "float32"},
        "acceleration": {
            "backend": "e3nn",
            "training_backend": "e3nn",
            "only_cueq": False,
            "require_available": False,
        },
    }


class _MigrationStore:
    def __init__(self, *, receipt: dict, previous_study: object, entry: object, smoke: dict):
        from mdstats.training_data import _campaign_cli_core as cli

        self.receipt = receipt
        self.previous_study = previous_study
        self.entry = entry
        self.payloads: dict[str, object] = {
            "prepare_restart_receipt": receipt,
            "model_sweep_checkpoint": receipt["model_sweep"],
            "preflight_smoke": smoke,
        }
        self.records: dict[str, object] = {
            key: {"record": key} for key in cli._PREPARE_REUSE_RECORD_KEYS
        }
        self.records.update({
            "source_catalog": SimpleNamespace(sources=()),
            "target_multi_view_repair_v2": SimpleNamespace(),
            "target_multi_view_qualification_v2": SimpleNamespace(),
            "production_qualification": SimpleNamespace(
                status=SimpleNamespace(value="passed"), full_data9a_passed=True
            ),
            "execution:old": {"record": "old execution"},
            "training_campaign": {"record": "old campaign"},
        })
        self.records["target_size_study"] = previous_study
        self.digests = {
            key: digest({"record": key})
            for key in cli._PREPARE_REUSE_RECORD_KEYS
        }
        self.stages = {
            "prepare": (cli.StageState.COMPLETE, "historical prepare"),
            "preflight": (cli.StageState.COMPLETE, "historical preflight"),
        }
        self.meta: dict[str, object] = {}

    def stage(self, name):
        from mdstats.training_data import _campaign_cli_core as cli

        return self.stages.get(name, (cli.StageState.NOT_STARTED, ""))

    def set_stage(self, name, state, message):
        self.stages[name] = (state, message)

    def get_meta(self, key):
        return self.meta.get(key)

    def set_meta(self, key, value):
        self.meta[key] = value

    def has_record(self, key):
        return key in self.records or key in self.payloads

    def get_payload(self, key):
        return self.payloads[key]

    def get_payload_optional(self, key):
        return self.payloads.get(key, self.records.get(key))

    def get_record(self, key, _cls):
        return self.records[key]

    def get_record_optional(self, key, _cls):
        return self.previous_study if key == "target_size_study" else None

    def record_digest(self, key):
        if key in self.digests:
            return self.digests[key]
        return digest(self.records[key])

    def record_keys(self, prefix=""):
        return tuple(sorted(key for key in self.records if key.startswith(prefix)))

    def put_record(self, key, value):
        if key == "preflight_smoke":
            self.payloads[key] = value
        elif key == "prepare_restart_receipt":
            self.payloads[key] = value
            self.records[key] = value
        else:
            self.records[key] = value

    def delete_record(self, key):
        self.records.pop(key, None)


def _migration_entry(cli, cfg: dict, *, current: bool):
    budget, learning_rate, admissibility, selection = cli._train2_policy_set(
        cfg, require_replay=True
    )
    optimizer = cli._optimizer_policy(cfg, seed=1, num_workers=1)
    if not current:
        old_cfg = _migration_cfg((3, 10, 30), 30)
        budget, learning_rate, admissibility, selection = cli._train2_policy_set(
            old_cfg, require_replay=True
        )
        optimizer = cli._optimizer_policy(old_cfg, seed=1, num_workers=1)
    protocol = SimpleNamespace(
        training_mode=SimpleNamespace(value="multihead_replay"),
        optimizer_policy=optimizer,
        training_budget_policy=budget,
        learning_rate_schedule_policy=learning_rate,
        checkpoint_admissibility_policy=admissibility,
        checkpoint_selection_policy=selection,
    )
    artifact = SimpleNamespace(
        bundle_digest="b" * 64,
        tree_digest="t" * 64,
        tree_entries=(
            ("jobs/job/target_train.xyz", _h("target")),
            ("jobs/job/target_valid.xyz", _h("valid")),
            ("jobs/job/mace_config.yaml", _h("schedule")),
            ("jobs/job/run_mace.sh", _h("command")),
            ("data8_preparation_bundle.json", _h("bundle")),
        ),
    )
    materialization = SimpleNamespace(
        checkpoint=SimpleNamespace(
            plan=SimpleNamespace(content_digest="p" * 64),
            data8_artifact=artifact,
        )
    )
    bundle = SimpleNamespace(
        content_digest="b" * 64,
        jobs=(SimpleNamespace(protocol=protocol),),
    )
    return SimpleNamespace(
        variant_id="multihead_replay-n512-seed1",
        materialization=materialization,
        bundle=bundle,
    )


@pytest.mark.parametrize(
    ("fidelity_epochs", "horizon", "old_schedule", "expected_first_epoch"),
    [
        ((1, 3, 10), 30, False, 1),
        ((2, 5, 12), 40, True, 2),
    ],
)
def test_supplemental_historical_upgrade_d1_d2_reuses_data_matrix_and_reopens_exact_frontier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    fidelity_epochs: tuple[int, int, int],
    horizon: int,
    old_schedule: bool,
    expected_first_epoch: int,
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    monkeypatch.setattr(cli, "_resolve_mace_loader_workers", lambda _cfg: (1, None, 0))
    current_cfg = _migration_cfg(fidelity_epochs, horizon)
    current_policy = mdstats.TargetSizeStudyPolicy(
        fidelity_epochs=fidelity_epochs,
        screening_optimizer_seeds=(1,),
    )
    previous_policy = mdstats.TargetSizeStudyPolicy(
        fidelity_epochs=(3, 10, 30),
        screening_optimizer_seeds=(1,),
    )
    previous_study = mdstats.build_target_size_study(
        _Repair(), _Qual(), policy=previous_policy, training_horizon_epochs=30
    )
    new_study = mdstats.build_target_size_study(
        _Repair(), _Qual(), policy=current_policy, training_horizon_epochs=horizon
    )
    assert previous_study.policy.policy_digest != new_study.policy.policy_digest
    entry = _migration_entry(cli, current_cfg, current=not old_schedule)
    paths = SimpleNamespace(
        config=tmp_path / "campaign.toml",
        manifest=tmp_path / "manifest.json",
        config_dir=tmp_path,
    )
    paths.config.write_text("[campaign]\nprofile = 'lta'\n", encoding="utf-8")
    paths.manifest.write_text("{}\n", encoding="utf-8")
    matrix_before = cli._data8_matrix_digest([entry])
    pointer = {
        "checkpoint_digest": "c" * 64,
        "plan_digest": "q" * 64,
        "status": "complete",
        "completed_frames": 1,
        "requested_frames": 1,
        "relative_directory": ".mdstats/model-sweep",
    }
    receipt = {
        "schema": cli._HISTORICAL_PREPARE_RESTART_RECEIPT_SCHEMA,
        "contract": {"contract": "current"},
        "config_sha256": "historical-config",
        "input_identities": [],
        "record_digests": {
            key: digest({"record": key}) for key in cli._PREPARE_REUSE_RECORD_KEYS
        },
        "model_sweep": pointer,
        "data8": [{
            "variant_id": entry.variant_id,
            "bundle_digest": entry.bundle.content_digest,
            "plan_digest": entry.materialization.checkpoint.plan.content_digest,
            "tree_digest": "t" * 64,
        }],
    }
    smoke = {
        "passed": True,
        "data8_matrix_digest": cli._legacy_data8_matrix_digest([entry]),
    }
    store = _MigrationStore(
        receipt=receipt,
        previous_study=previous_study,
        entry=entry,
        smoke=smoke,
    )
    monkeypatch.setattr(cli, "_prepare_contract_signature", lambda: {"contract": "current"})
    monkeypatch.setattr(cli, "_historical_prepare_inputs_match_current", lambda *_args: True)
    monkeypatch.setattr(cli, "_current_data8_entries", lambda _store: [entry])
    monkeypatch.setattr(cli, "_target_size_materialization_variants", lambda _cfg, *, study: (SimpleNamespace(variant_id=entry.variant_id),))
    monkeypatch.setattr(cli, "_ensure_target_size_study", lambda *_args, **_kwargs: new_study)
    monkeypatch.setattr(cli, "_validate_train2_data8_matrix", lambda *_args: None)
    monkeypatch.setattr(cli, "_stage_config_digest", lambda _paths, name: f"current-{name}")

    reused = cli._try_reuse_completed_prepare(current_cfg, paths, store)
    if old_schedule:
        assert reused is False
        current_entry = _migration_entry(cli, current_cfg, current=True)
        assert cli._train2_data8_schedule_matches_config(current_cfg, [current_entry])
    else:
        assert reused is True
    assert cli._data8_matrix_digest([entry]) == matrix_before
    assert new_study.next_training_epoch == expected_first_epoch
    assert store.stage("preflight")[0] is cli.StageState.COMPLETE
    assert "historical:train2-invalidation:training_campaign:" in "\n".join(store.records)
    assert "training_campaign" not in store.records
    assert store.payloads["preflight_smoke"]["data8_matrix_digest"] == matrix_before


def test_supplemental_case_d3_preparation_change_rejects_completed_reuse_before_data_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    receipt = {
        "schema": cli.PREPARE_RESTART_RECEIPT_SCHEMA,
        "contract": {"contract": "current"},
        "config_sha256": "old-config",
        "preparation_config_digest": "old-preparation",
    }

    class Store:
        def stage(self, name):
            return cli.StageState.COMPLETE, "done"

        def has_record(self, key):
            return key in {"prepare_restart_receipt", "source_catalog"}

        def get_payload(self, key):
            return receipt

        def get_record(self, key, _cls):
            return SimpleNamespace(sources=())

    monkeypatch.setattr(cli, "_prepare_contract_signature", lambda: {"contract": "current"})
    monkeypatch.setattr(cli, "_preparation_config_digest", lambda _cfg: "new-preparation")
    monkeypatch.setattr(cli, "_sha256", lambda _path: "new-config")
    paths = SimpleNamespace(config=tmp_path / "campaign.toml")
    assert not cli._try_reuse_completed_prepare({}, paths, Store())


@pytest.mark.parametrize(
    ("index", "replacement"),
    [(0, [2, 3, 10]), (1, [1, 5, 10]), (2, [1, 3, 12])],
)
def test_preparation_identity_excludes_each_independent_fidelity_boundary(
    index: int, replacement: list[int]
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    base = {
        "schema": "mdstats.mlff-campaign-cli.v2",
        "target_data": {"size_convergence": {"fidelity_epochs": [1, 3, 10]}},
        "training": {"policy_generation": "train2", "max_num_epochs": 30},
    }
    changed = {
        **base,
        "target_data": {"size_convergence": {"fidelity_epochs": replacement}},
    }
    assert replacement[index] != base["target_data"]["size_convergence"]["fidelity_epochs"][index]
    assert cli._preparation_config_digest(base) == cli._preparation_config_digest(changed)


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
    historical = mdstats.authenticated_fixed_predecessor_candidate_authority(legacy)
    assert historical["generation"] == mdstats.LEGACY_FIXED_CANDIDATE_AUTHORITY_GENERATION
    assert historical["historical_policy_digest"] == old_policy["policy_digest"]
    assert historical["candidate_authority_digest"] != current.candidate_authority_digest
    migrated = mdstats.TargetSizeStudyPlan.from_dict(legacy)
    assert migrated.policy.fidelity_epochs == (3, 10, 30)
    assert migrated.outcome == mdstats.OUTCOME_AWAITING_COARSE_SCREEN
    legacy["qualified_sizes"] = [512]
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        mdstats.TargetSizeStudyPlan.from_dict(legacy)
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        mdstats.authenticated_fixed_predecessor_candidate_authority(legacy)


def test_historical_fixed_authority_is_captured_before_v8_study_migration(
    tmp_path: Path,
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    current = mdstats.build_target_size_study(
        _Repair(), _Qual(),
        policy=mdstats.TargetSizeStudyPolicy(fidelity_epochs=(1, 3, 10)),
        training_horizon_epochs=30,
    )
    legacy = _authentic_fixed_predecessor_payload(current)
    store = cli.CampaignStore(tmp_path / "campaign.sqlite3")
    store.put_record("target_size_study", legacy)
    cli._capture_historical_fixed_candidate_authority(store)
    receipt = store.get_payload(cli._HISTORICAL_FIXED_CANDIDATE_AUTHORITY_KEY)
    assert receipt == mdstats.authenticated_fixed_predecessor_candidate_authority(legacy)
    # Reopening proves that the raw v6 policy identity survives the later
    # v8-to-flexible normalization boundary as compatibility evidence.
    store.close()
    reopened = cli.CampaignStore(tmp_path / "campaign.sqlite3")
    cli._capture_historical_fixed_candidate_authority(reopened)
    assert reopened.get_payload(cli._HISTORICAL_FIXED_CANDIDATE_AUTHORITY_KEY) == receipt
    reopened.close()


def test_stage_local_real_store_captures_fixed_authority_before_flexible_rebuild(
    tmp_path: Path,
) -> None:
    """Exercise raw v8/v6 capture and the real current study owner together."""

    from mdstats.training_data import _campaign_cli_core as cli

    repair, qualification = _persistable_target_size_authorities()
    legacy_current = mdstats.build_target_size_study(
        repair,
        qualification,
        policy=mdstats.TargetSizeStudyPolicy(
            fidelity_epochs=(3, 10, 30), screening_optimizer_seeds=(1,)
        ),
        training_horizon_epochs=30,
    )
    store = cli.CampaignStore(tmp_path / "campaign.sqlite3")
    store.put_records({
        "target_multi_view_repair_v2": repair,
        "target_multi_view_qualification_v2": qualification,
        "target_size_study": _authentic_fixed_predecessor_payload(legacy_current),
    })
    current = cli._ensure_target_size_study(
        store,
        cfg=_migration_cfg((1, 3, 10), 30),
        repair2=repair,
        mvqual2=qualification,
    )
    assert current.policy.fidelity_epochs == (1, 3, 10)
    historical = store.get_payload(cli._HISTORICAL_FIXED_CANDIDATE_AUTHORITY_KEY)
    assert historical["candidate_authority_digest"] != current.candidate_authority_digest
    assert historical["dataset_id"] == current.dataset_id
    assert historical["candidate_digests"] == list(current.candidate_authority_inputs["candidate_digests"])
    store.close()


def _authentic_fixed_predecessor_payload(study: object) -> dict[str, object]:
    """Return raw v8/v6 evidence for focused bridge-unit coverage only."""

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
    payload: dict[str, object] = {
        "schema": "mdstats.target-size-study-plan.v8",
        "authority_version": "mdstats.target-size-study.fixed-eight.2026-08.v5.3",
        "dataset_id": study.dataset_id,
        "repair2_authority_digest": study.repair2_authority_digest,
        "mvqual_authority_digest": study.mvqual_authority_digest,
        "policy": old_policy,
        "candidates": [item.to_dict() for item in study.candidates],
        "qualified_sizes": list(study.qualified_sizes),
        "epoch3_outcomes": [], "epoch3_survivor_sizes": [],
        "epoch10_outcomes": [], "epoch10_finalist_sizes": [], "epoch30_outcomes": [],
        "selected_target_size": None, "outcome": "awaiting_epoch_3",
        "decision_reason": "legacy fixture", "comparison_failure_stage": None,
        "comparison_failures": [],
    }
    payload["content_digest"] = digest(payload)
    return payload


def _fixed_predecessor_bridge_entry(*, authority_digest: str, plan_schema: str):
    """A bounded external DATA8 artifact below the bridge-owner boundary."""

    bundle = SimpleNamespace(content_digest=_h("legacy-data8-bundle"))
    protocol = SimpleNamespace(
        training_mode=SimpleNamespace(value="multihead_replay"),
        selection_size=512,
        optimizer_policy=SimpleNamespace(seed=1),
    )
    bundle.jobs = (
        SimpleNamespace(
            kind=SimpleNamespace(value="final_development"),
            fold_index=None,
            protocol=protocol,
        ),
    )
    artifact = SimpleNamespace(
        bundle_digest=bundle.content_digest,
        tree_digest=_h("legacy-data8-tree"),
    )
    plan = SimpleNamespace(
        plan_schema=plan_schema,
        selection_authority_role="target_size_candidate",
        target_size_study_digest=authority_digest,
        content_digest=_h("legacy-materialization-plan"),
    )
    materialization = SimpleNamespace(
        checkpoint=SimpleNamespace(plan=plan, data8_artifact=artifact),
        load_data8_bundle=lambda: bundle,
    )
    return SimpleNamespace(
        variant_id="multihead_replay-n512-seed1",
        bundle=bundle,
        materialization=materialization,
    )


def test_supplemental_fixed_predecessor_data8_authority_bridge_is_explicit_and_idempotent(
    tmp_path: Path,
) -> None:
    """The bridge verifies the old generation rather than accepting a mismatch."""

    from mdstats.training_data import _campaign_cli_core as cli

    study = mdstats.build_target_size_study(
        _Repair(), _Qual(),
        policy=mdstats.TargetSizeStudyPolicy(fidelity_epochs=(1, 3, 10)),
        training_horizon_epochs=30,
    )
    store = cli.CampaignStore(tmp_path / "campaign.sqlite3")
    historical = mdstats.authenticated_fixed_predecessor_candidate_authority(
        _authentic_fixed_predecessor_payload(study)
    )
    store.put_record(cli._HISTORICAL_FIXED_CANDIDATE_AUTHORITY_KEY, historical)
    entry = _fixed_predecessor_bridge_entry(
        authority_digest=historical["candidate_authority_digest"],
        # This deliberately proves the bridge does not classify authority by
        # production serialization generation.
        plan_schema="mdstats.production-materialization-plan.v10",
    )
    cli._fixed_predecessor_data8_authority_bridge(store, study, [entry])
    key = f"target_size_data8_authority_bridge:{study.candidate_authority_digest}"
    receipt = store.get_payload(key)
    assert receipt["predecessor_generation"] == "fixed-fidelity-policy-bound.v1"
    assert receipt["current_generation"] == "flexible-fidelity-candidate-prefix.v1"
    assert receipt["entries"][0]["data8_bundle_digest"] == entry.bundle.content_digest
    # A repeated restart uses the same immutable DATA8 binding without adding
    # a second bridge record or rewriting the scientific artifact.
    cli._fixed_predecessor_data8_authority_bridge(store, study, [entry])
    assert store.record_keys("target_size_data8_authority_bridge:") == (key,)
    store.close()
    # The compact fixture remains unit coverage, but it proves receipt
    # idempotence across the actual SQLite persistence boundary.
    reopened = cli.CampaignStore(tmp_path / "campaign.sqlite3")
    cli._fixed_predecessor_data8_authority_bridge(reopened, study, [entry])
    assert reopened.record_keys("target_size_data8_authority_bridge:") == (key,)
    reopened.close()


@pytest.mark.parametrize("mismatch", ["wrong-authority", "missing-evidence"])
def test_supplemental_fixed_predecessor_data8_authority_bridge_fails_closed(
    tmp_path: Path, mismatch: str
) -> None:
    from mdstats.training_data import _campaign_cli_core as cli

    study = mdstats.build_target_size_study(_Repair(), _Qual())
    historical = mdstats.authenticated_fixed_predecessor_candidate_authority(
        _authentic_fixed_predecessor_payload(study)
    )
    entry = _fixed_predecessor_bridge_entry(
        authority_digest=(
            _h(mismatch) if mismatch == "wrong-authority"
            else historical["candidate_authority_digest"]
        ),
        plan_schema="mdstats.production-materialization-plan.v10",
    )
    store = cli.CampaignStore(tmp_path / "campaign.sqlite3")
    if mismatch != "missing-evidence":
        store.put_record(cli._HISTORICAL_FIXED_CANDIDATE_AUTHORITY_KEY, historical)
    with pytest.raises(cli.CampaignCliError, match="(fixed-fidelity authority|fixed v8/v6 predecessor evidence)"):
        cli._fixed_predecessor_data8_authority_bridge(store, study, [entry])
    assert not store.record_keys("target_size_data8_authority_bridge:")
    store.close()
