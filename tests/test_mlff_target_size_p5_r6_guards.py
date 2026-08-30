"""Mandatory negative guards for P5-R6: Post-selection CV & Final Production.

Covers all 16 required negative guards:
 1. guard_p5_method_drift_rejects_authorization
 2. guard_p5_learning_rate_schedule_mismatch
 3. guard_p5_optimizer_policy_mismatch
 4. guard_p5_common_training_policy_mismatch
 5. guard_p5_checkpoint_admissibility_mismatch
 6. guard_p5_checkpoint_selection_mismatch
 7. guard_p5_replay_exposure_mismatch
 8. guard_p5_mace_architecture_mismatch
 9. guard_p5_unauthorized_production_fails_closed
10. guard_p5_failed_cv_cannot_authorize_production
11. guard_p5_multihead_replay_without_source_fails_closed
12. guard_p5_non_dft_replay_labels_rejected
13. guard_p5_tampered_mace_config_fails_closed
14. guard_p5_tampered_materialization_fails_closed
15. guard_p5_cross_campaign_authorization_rejected
16. guard_p5_modified_selection_invalidates_authorization
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    fixture_config_text,
    load_context,
    rewrite_config,
    run_cross_validate,
    run_train_production,
)

import mdstats
from mdstats.training_data.campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
)
from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.eval2 import assess_eval2_checkpoint
from mdstats.training_data.post_selection_cv_acceptance import (
    CvCampaignAcceptance,
    require_cv_acceptance_for_method,
)
from mdstats.training_data.post_selection_execution import (
    PostSelectionExecutionError,
    authenticate_post_selection_provider,
    materialize_post_selection_run,
)
from mdstats.training_data.post_selection_identity import (
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from mdstats.training_data.post_selection_production import (
    build_final_production_plan,
    validate_final_production_plan,
)


def _setup_cv_accepted_campaign(tmp_path: Path):
    config, workspace = build_selected_campaign(tmp_path)
    harness = PostSelectionHarness()
    rc = run_cross_validate(config, harness)
    assert rc == 0
    return config, workspace, harness


# Guard 1: Method drift rejects authorization
def test_guard_p5_method_drift_rejects_authorization(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\n[weighting]\npolicy = "energy_exponential"',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 2: Learning rate schedule mismatch
def test_guard_p5_learning_rate_schedule_mismatch(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\ntrain2_final_lr_multiplier = 0.05',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 3: Optimizer policy mismatch
def test_guard_p5_optimizer_policy_mismatch(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\noptimizer = "adamw"',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 4: Common training policy mismatch
def test_guard_p5_common_training_policy_mismatch(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\n[objective]\nforces_weight = 5.0',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 5: Checkpoint admissibility mismatch
def test_guard_p5_checkpoint_admissibility_mismatch(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\n[acceptance]\nmaximum_target_force_rmse_ev_per_angstrom = 0.001',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 6: Checkpoint selection mismatch
def test_guard_p5_checkpoint_selection_mismatch(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\n[acceptance]\nallowed_replay_degradation_mev_per_a = 1.0',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 7: Replay exposure mismatch
def test_guard_p5_replay_exposure_mismatch(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\ntraining_mode = "multihead_replay"',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 8: MACE architecture mismatch
def test_guard_p5_mace_architecture_mismatch(tmp_path: Path):
    config, _, harness = _setup_cv_accepted_campaign(tmp_path)
    rewrite_config(
        config,
        'policy_generation = "train2"',
        'policy_generation = "train2"\n[model]\nr_max = 6.0',
    )
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 9: Unauthorized production fails closed
def test_guard_p5_unauthorized_production_fails_closed(tmp_path: Path):
    config, _ = build_selected_campaign(tmp_path)
    harness = PostSelectionHarness()
    with pytest.raises(PostSelectionError):
        run_train_production(config, harness)


# Guard 10: Failed CV cannot authorize production
def test_guard_p5_failed_cv_cannot_authorize_production(tmp_path: Path):
    config, _ = build_selected_campaign(tmp_path)
    # Set an impossible acceptance threshold so CV rejects
    rewrite_config(config, "acceptance_maximum = 0.5", "acceptance_maximum = 0.00001")
    harness = PostSelectionHarness()
    with pytest.raises(PostSelectionError, match="rejected the training method"):
        run_cross_validate(config, harness)
    with pytest.raises(Exception):
        run_train_production(config, harness)


# Guard 11: Multihead replay without source fails closed
def test_guard_p5_multihead_replay_without_source_fails_closed():
    cfg = {
        "training": {"training_mode": "multihead_replay"},
        "model": {},
        "acceptance": {},
        "acceleration": {},
        "paths": {},
        "objective": {},
        "weighting": {},
        "atomic_references": {},
    }
    with pytest.raises(Exception):
        resolve_post_selection_method_policies(cfg)


# Guard 12: Non-DFT replay labels rejected
def test_guard_p5_non_dft_replay_labels_rejected():
    from mdstats.training_data.eval2 import (
        Eval2TrajectoryPoint,
        Eval2TargetMetricRecord,
        Eval2TargetBlockMetric,
        assess_eval2_checkpoint,
    )
    from mdstats.training_data.train2_policy import CheckpointAdmissibilityPolicy

    pt = Eval2TrajectoryPoint(
        epoch=1,
        checkpoint_sha256="a" * 64,
        lightweight_target_score_ev_per_angstrom=0.01,
        normalized_schedule_progress=0.5,
        instantaneous_learning_rate=1.0e-4,
        phase="adaptation",
        runtime_summary_digest="e" * 64,
        stable_candidate_identity="cand_1",
    )
    block = Eval2TargetBlockMetric(
        block_id="b1",
        force_squared_error_sum=0.01,
        force_component_count=100,
        configuration_count=10,
    )
    t_metrics = Eval2TargetMetricRecord(
        configuration_count=10,
        atom_count=100,
        energy_mae_ev_per_atom=0.001,
        relative_energy_rmse_ev_per_atom=None,
        force_component_rmse_ev_per_angstrom=0.01,
        species_macro_force_rmse_ev_per_angstrom=0.01,
        species_force_rmse_ev_per_angstrom=(("Si", 0.01),),
        force_error_p90_ev_per_angstrom=0.01,
        force_error_p95_ev_per_angstrom=0.01,
        force_error_p99_ev_per_angstrom=0.01,
        worst_stratum_force_rmse_ev_per_angstrom=None,
        stratum_force_rmse_ev_per_angstrom=(),
        stress_rmse_ev_per_angstrom3=None,
        block_metrics=(block,),
        target_role_digest="b" * 64,
        prediction_digest="c" * 64,
    )
    admissibility = CheckpointAdmissibilityPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.030,
        replay_enabled=True,
        replay_degradation_budget_ev_per_angstrom=0.05,
        replay_label_requirement="true_dft",
    )
    record = assess_eval2_checkpoint(
        pt,
        evaluation_record_digest="d" * 64,
        target_metrics=t_metrics,
        admissibility_policy=admissibility,
        replay_candidate_force_rmse_ev_per_angstrom=0.02,
        replay_foundation_force_rmse_ev_per_angstrom=0.02,
        replay_label_mode="foundation_baseline",  # Non-DFT label rejected!
    )
    assert not record.admissible
    assert "replay_true_dft_evidence_missing" in record.rejection_reasons


# Guard 13: Tampered MACE config fails closed
def test_guard_p5_tampered_mace_config_fails_closed(tmp_path: Path):
    config, _workspace, harness = _setup_cv_accepted_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=harness.train)
        plan = resolve_current_cv_plan(context)
        assert plan is not None
        seed = plan.required_cv_seeds[0]
        from mdstats.training_data.post_selection_cv_plan import (
            build_cv_fold_run_plan,
        )

        run_plan = build_cv_fold_run_plan(
            plan,
            fold_index=0,
            optimizer_seed=seed,
            planned_epochs=context.cv_policy.cv_max_num_epochs,
        )
        run_root = context.run_root(run_plan.run_identity)
        config_file = run_root / "materialization" / "post_selection_mace_config.yaml"
        assert config_file.is_file()
        config_file.write_text("tampered: true\n")
        mat_path = run_root / "materialization" / "materialization.json"
        from mdstats.training_data.post_selection_execution import (
            PostSelectionMaterialization,
            authenticate_post_selection_provider,
        )

        mat = PostSelectionMaterialization.from_dict(
            json.loads(mat_path.read_text(encoding="utf-8"))
        )
        with pytest.raises(PostSelectionExecutionError):
            authenticate_post_selection_provider(
                materialization=mat,
                materialization_directory=run_root / "materialization",
                checkpoint_directory=run_root / "checkpoints",
                checkpoint_name="chk.pt",
                checkpoint_sha256="a" * 64,
                summary=object(),
                evaluation_model_state="model_state",
                allow_forward_override=False,
            )
    finally:
        store.close()


# Guard 14: Tampered materialization fails closed
def test_guard_p5_tampered_materialization_fails_closed(tmp_path: Path):
    config, _workspace, harness = _setup_cv_accepted_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=harness.train)
        plan = resolve_current_cv_plan(context)
        assert plan is not None
        seed = plan.required_cv_seeds[0]
        from mdstats.training_data.post_selection_cv_plan import (
            build_cv_fold_run_plan,
        )

        run_plan = build_cv_fold_run_plan(
            plan,
            fold_index=0,
            optimizer_seed=seed,
            planned_epochs=context.cv_policy.cv_max_num_epochs,
        )
        run_root = context.run_root(run_plan.run_identity)
        mat_file = run_root / "materialization" / "materialization.json"
        assert mat_file.is_file()
        from mdstats.training_data.target_size_execution import (
            publish_immutable_json_create_or_verify,
        )
        from mdstats.training_data.post_selection_execution import (
            PostSelectionMaterialization,
        )

        with pytest.raises(Exception):
            publish_immutable_json_create_or_verify(
                mat_file,
                {"tampered": True},
                deserializer=PostSelectionMaterialization.from_dict,
            )
    finally:
        store.close()


# Guard 15: Cross-campaign authorization rejected
def test_guard_p5_cross_campaign_authorization_rejected(tmp_path: Path):
    config, _workspace, harness = _setup_cv_accepted_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=harness.train)
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        assert plan is not None and acceptance is not None
        from mdstats.training_data.campaign_post_selection import PostSelectionBinding

        b = context.selected.binding
        fake_binding = PostSelectionBinding(
            campaign_generation=b.campaign_generation + 1,  # Different generation!
            campaign_state_revision=b.campaign_state_revision,
            experiment_definition_digest=b.experiment_definition_digest,
            training_order_digest=b.training_order_digest,
            frame_authority_digest=b.frame_authority_digest,
            neutral_statistical_base_digest=b.neutral_statistical_base_digest,
            split_exclusion_digest=b.split_exclusion_digest,
            target_size_policy_digest=b.target_size_policy_digest,
            aggregate_digest=b.aggregate_digest,
            adopted_execution_head_digest=b.adopted_execution_head_digest,
            adopted_reducer_state_digest=b.adopted_reducer_state_digest,
            n_selected=b.n_selected,
            selected_membership_digest=b.selected_membership_digest,
        )
        fake_selected = CurrentSelectedTrainingContext(
            binding=fake_binding,
            selected_membership=context.selected.selected_membership,
            validated_terminal_result=context.selected.validated_terminal_result,
            authorities=context.selected.authorities,
        )
        with pytest.raises(PostSelectionError):
            build_final_production_plan(
                fake_selected,
                context.method,
                context.production_policy,
                cv_plan=plan,
                cv_acceptance=acceptance,
            )
    finally:
        store.close()


# Guard 16: Modified selection invalidates authorization
def test_guard_p5_modified_selection_invalidates_authorization(tmp_path: Path):
    config, _workspace, harness = _setup_cv_accepted_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=harness.train)
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        assert plan is not None and acceptance is not None
        from mdstats.training_data.campaign_post_selection import PostSelectionBinding

        b = context.selected.binding
        fake_binding = PostSelectionBinding(
            campaign_generation=b.campaign_generation,
            campaign_state_revision=b.campaign_state_revision,
            experiment_definition_digest=b.experiment_definition_digest,
            training_order_digest=b.training_order_digest,
            frame_authority_digest=b.frame_authority_digest,
            neutral_statistical_base_digest=b.neutral_statistical_base_digest,
            split_exclusion_digest=b.split_exclusion_digest,
            target_size_policy_digest=b.target_size_policy_digest,
            aggregate_digest=b.aggregate_digest,
            adopted_execution_head_digest=b.adopted_execution_head_digest,
            adopted_reducer_state_digest=b.adopted_reducer_state_digest,
            n_selected=b.n_selected - 1,
            selected_membership_digest="f" * 64,
        )
        fake_selected = CurrentSelectedTrainingContext(
            binding=fake_binding,
            selected_membership=context.selected.selected_membership[:-1],  # dropped one frame
            validated_terminal_result=context.selected.validated_terminal_result,
            authorities=context.selected.authorities,
        )
        with pytest.raises(PostSelectionError):
            build_final_production_plan(
                fake_selected,
                context.method,
                context.production_policy,
                cv_plan=plan,
                cv_acceptance=acceptance,
            )
    finally:
        store.close()
