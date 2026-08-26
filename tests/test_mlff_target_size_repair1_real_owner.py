"""Disk-backed real-owner baseline for Target-Size Repair-1.

This module deliberately owns only acceptance that it can exercise without
replacing a semantic owner: current TOML normalization, SQLite persistence,
and current REPAIR2/MVQUAL2 target-size reconstruction.  DATA8/runtime tests
belong here only once they execute their real owners as well.
"""
from __future__ import annotations

import ast
import argparse
from pathlib import Path

import mdstats
import pytest


def _authorities() -> tuple[object, object]:
    # The existing fixture builds native, fully serializable REPAIR2/MVQUAL2
    # records.  It supplies bounded scientific inputs, not a target-size state
    # transition or persistence replacement.
    from tests.test_mlff_flexible_fidelity import _persistable_target_size_authorities

    return _persistable_target_size_authorities()


def _campaign(tmp_path: Path, *, fidelity: tuple[int, int, int] = (1, 3, 10), horizon: int = 30):
    from mdstats.training_data import _campaign_cli_core as cli

    tmp_path.mkdir(parents=True, exist_ok=True)
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
    config.write_text(
        config.read_text(encoding="utf-8")
        .replace("fidelity_epochs = [1, 3, 10]", f"fidelity_epochs = {list(fidelity)}")
        .replace("max_num_epochs = 30", f"max_num_epochs = {horizon}", 1),
        encoding="utf-8",
    )
    cfg, paths = cli._load_config(config)
    paths.ensure()
    store = cli.CampaignStore(paths.state_db)
    repair, qualification = _authorities()
    store.put_records(
        {
            "target_multi_view_repair_v2": repair,
            "target_multi_view_qualification_v2": qualification,
        }
    )
    cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "bounded fixture")
    return config, cfg, paths, store, repair, qualification


def test_real_store_reopens_current_screen_unchanged_when_only_production_horizon_changes(tmp_path: Path) -> None:
    """Production n is outside current target-size study identity (R3A baseline)."""

    from mdstats.training_data import _campaign_cli_core as cli

    config, cfg, paths, store, repair, qualification = _campaign(tmp_path)
    initial = cli._ensure_target_size_study(
        store, cfg=cfg, repair2=repair, mvqual2=qualification
    )
    assert initial.screening_horizon_epochs == 10
    assert initial.next_training_epoch == 1
    store.close()

    config.write_text(
        config.read_text(encoding="utf-8").replace("max_num_epochs = 30", "max_num_epochs = 40", 1),
        encoding="utf-8",
    )
    changed_cfg, changed_paths = cli._load_config(config)
    reopened = cli.CampaignStore(changed_paths.state_db)
    restored_repair = reopened.get_record(
        "target_multi_view_repair_v2", mdstats.TargetMultiViewRepairPlanV2
    )
    restored_qualification = reopened.get_record(
        "target_multi_view_qualification_v2", mdstats.TargetMultiViewQualificationPlanV2
    )
    resumed = cli._ensure_target_size_study(
        reopened,
        cfg=changed_cfg,
        repair2=restored_repair,
        mvqual2=restored_qualification,
    )

    assert resumed.content_digest == initial.content_digest
    assert resumed.screening_horizon_epochs == 10
    assert resumed.next_training_epoch == 1
    assert paths.state_db == changed_paths.state_db
    reopened.close()


def test_real_store_rebuilds_screen_for_a_current_fidelity_change(tmp_path: Path) -> None:
    """A boundary edit is a new screen authority, unlike a production-n edit."""

    from mdstats.training_data import _campaign_cli_core as cli

    config, cfg, paths, store, repair, qualification = _campaign(tmp_path)
    initial = cli._ensure_target_size_study(
        store, cfg=cfg, repair2=repair, mvqual2=qualification
    )
    store.close()
    config.write_text(
        config.read_text(encoding="utf-8").replace("fidelity_epochs = [1, 3, 10]", "fidelity_epochs = [2, 5, 12]"),
        encoding="utf-8",
    )
    changed_cfg, changed_paths = cli._load_config(config)
    reopened = cli.CampaignStore(changed_paths.state_db)
    resumed = cli._ensure_target_size_study(
        reopened,
        cfg=changed_cfg,
        repair2=reopened.get_record("target_multi_view_repair_v2", mdstats.TargetMultiViewRepairPlanV2),
        mvqual2=reopened.get_record("target_multi_view_qualification_v2", mdstats.TargetMultiViewQualificationPlanV2),
    )

    assert resumed.content_digest != initial.content_digest
    assert resumed.policy.fidelity_epochs == (2, 5, 12)
    assert resumed.screening_horizon_epochs == 12
    assert resumed.next_training_epoch == 2
    reopened.close()


@pytest.mark.parametrize(
    ("command_name", "expected"),
    (
        ("command_train", "target-size flexible-fidelity experiment is owned"),
        ("command_evaluate", "Target-size endpoint comparison is owned"),
    ),
)
def test_active_screen_public_commands_fail_closed_without_mutating_real_store(
    tmp_path: Path, command_name: str, expected: str
) -> None:
    """The public production commands cannot become a second screen scheduler.

    This deliberately passes a normal generated TOML and a disk-backed
    ``CampaignStore`` through the public command guard.  It does not replace
    configuration parsing, target-study authentication, or persistence.
    """

    from mdstats.training_data import _campaign_cli_core as cli

    config, cfg, paths, store, repair, qualification = _campaign(tmp_path)
    initial = cli._ensure_target_size_study(
        store, cfg=cfg, repair2=repair, mvqual2=qualification
    )
    initial_doctor = cli._effective_stage(store, paths, "doctor")
    store.close()

    command = getattr(cli, command_name)
    with pytest.raises(cli.CampaignCliError, match=expected):
        command(argparse.Namespace(config=config))

    reopened = cli.CampaignStore(paths.state_db)
    try:
        restored = cli._load_verified_target_size_study_authority(reopened)
        assert restored.content_digest == initial.content_digest
        assert cli._effective_stage(reopened, paths, "doctor") == initial_doctor
    finally:
        reopened.close()


def test_real_promoted_data8_with_production_budget_fails_screen_schedule_authorization(
    tmp_path: Path,
) -> None:
    """A real promoted DATA8 tree cannot authorize a screen with its production n.

    The small materialization fixture supplies only the external scientific
    inputs.  DATA7/DATA8 materialization, the promoted-tree loader, DATA8
    discovery, and the TRAIN2 schedule owner all run unchanged here.  The
    intentionally wrong input is the real TRAIN2 plan's 30-epoch budget.
    """

    from mdstats.training_data import _campaign_cli_core as cli
    from tests.test_mlff_data9a9b_production_materialization import _fixture

    config, cfg, _, store, repair, qualification = _campaign(tmp_path / "campaign")
    study = cli._ensure_target_size_study(
        store, cfg=cfg, repair2=repair, mvqual2=qualification
    )
    inputs = _fixture(tmp_path / "materialization")
    sources, frames, _, data4, data5, data6, sweep, legacy_plan, _ = inputs
    domains = mdstats.build_feature_fit_domains(data5, cross_validation_plans=())
    selection_size = 4
    prefixes = {
        domain.content_digest: tuple(domain.frame_uids[:selection_size])
        for domain in domains
    }
    evaluation_frames = {
        domain.label_domain_id: tuple(domain.frame_uids[selection_size:])
        for domain in domains
        if domain.kind is mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT
    }
    true_replay = mdstats.inspect_replay_extxyz(
        Path(legacy_plan.replay_plan.monitor_artifact.path),
        label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )
    budget, learning_rate, admissibility, selection = cli._train2_policy_set(
        cfg, require_replay=True, planned_epochs=30
    )
    loader_workers = cli._resolve_mace_loader_workers(cfg)[0]
    production_budget_plan = mdstats.build_production_materialization_plan(
        sources,
        frames,
        data4,
        data5,
        data6,
        sweep,
        foundation_checkpoint=legacy_plan.foundation_checkpoint,
        compatibility_probe=legacy_plan.compatibility_probe,
        replay_plan=legacy_plan.replay_plan,
        cross_validation_plans=(),
        online_monitor_policy=mdstats.OnlineMonitorPolicy(
            target_configurations=1,
            replay_configurations=1,
            training_diagnostic_configurations=1,
        ),
        true_replay_monitor_artifact=true_replay,
        training_budget_policy=budget,
        learning_rate_schedule_policy=learning_rate,
        checkpoint_admissibility_policy=admissibility,
        checkpoint_selection_policy=selection,
        feature_metric_policy=legacy_plan.feature_metric_policy,
        atomic_reference_policy=legacy_plan.atomic_reference_policy,
        objective_policy=legacy_plan.objective_policy,
        configuration_weight_policy=legacy_plan.configuration_weight_policy,
        checkpoint_metric_policy=legacy_plan.checkpoint_metric_policy,
        selection_budget_policy=mdstats.SelectionBudgetPolicy(target_sizes=(selection_size,)),
        compatibility_policy=legacy_plan.compatibility_policy,
        optimizer_policy=cli._optimizer_policy(
            cfg, seed=1, num_workers=loader_workers, planned_epochs=30
        ),
        checkpoint_control_policy=legacy_plan.checkpoint_control_policy,
        extxyz_policy=legacy_plan.extxyz_policy,
        foundation_reference_energies=dict(legacy_plan.foundation_reference_energies),
        selection_size=selection_size,
        selection_authority_role="target_size_candidate",
        target_size_study_digest=study.candidate_authority_digest,
        prescribed_training_domain_prefixes=prefixes,
        prescribed_target_size_evaluation_frames=evaluation_frames,
        require_foundation_residual_e0=False,
        require_replay=True,
    )
    materialization = mdstats.run_restartable_production_materialization(
        sources,
        frames,
        inputs[2],
        data4,
        data5,
        data6,
        sweep,
        production_budget_plan,
        tmp_path / "materialized",
    )
    assert materialization.complete
    bundle = materialization.load_data8_bundle()
    variant_id = "multihead_replay-n4-seed1"
    store.put_records(
        {
            f"data8:{variant_id}": bundle,
            f"materialization:{variant_id}": materialization,
        }
    )
    store.set_meta("data8_variants", [variant_id])
    entries = cli._current_data8_entries(store)

    assert len(entries) == 1
    assert entries[0].root == Path(materialization.data8_runtime_directory).resolve()
    assert bundle.jobs[0].protocol.training_budget_policy.planned_epochs == 30
    assert not cli._train2_data8_schedule_matches_config(cfg, entries, study=study)
    store.close()


def test_repair1_real_owner_module_does_not_replace_forbidden_owners() -> None:
    """Keep gate tests sensitive to the owners they claim to exercise."""

    forbidden = {
        "_load_config",
        "CampaignStore",
        "_ensure_target_size_study",
        "_current_data8_entries",
        "_validate_train2_data8_matrix",
        "_train2_data8_schedule_matches_config",
        "_require_train2_preflight_authorization",
        "_build_campaign",
        "_train2_policy_set",
        "_optimizer_policy",
        "_invalidate_train2_downstream_state",
    }
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    patched = {
        argument.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"setattr", "patch", "patch.object"}
        for argument in node.args
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
    }
    assert not forbidden & patched
    source = Path(__file__).read_text(encoding="utf-8")
    assert "monkey" "patch" not in source
    assert "unittest." "mock" not in source
