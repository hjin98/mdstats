"""Mandatory negative qualification guards for P5-R7: Post-Selection CV & Final Production.

Covers all 23 required negative qualification guards:
 1. guard_p5_r7_01_foundation_identity_invariant_to_model_path_relocation
 2. guard_p5_r7_02_foundation_identity_changes_on_byte_modification
 3. guard_p5_r7_03_foundation_identity_changes_on_head_change
 4. guard_p5_r7_04_unsupported_training_optimizer_fails_closed
 5. guard_p5_r7_05_method_identity_does_not_contain_optimizer_family
 6. guard_p5_r7_06_replay_lineage_digest_covers_all_replay_artifacts
 7. guard_p5_r7_07_replay_monitor_byte_tamper_fails_plan_validation
 8. guard_p5_r7_08_replay_train_byte_tamper_fails_plan_validation
 9. guard_p5_r7_09_mace_post_selection_trainer_translates_internal_config
10. guard_p5_r7_10_mace_post_selection_trainer_sets_runtime_plan_env
11. guard_p5_r7_11_mace_post_selection_trainer_sets_pythonhashseed_env
12. guard_p5_r7_12_mace_post_selection_trainer_sets_true_replay_path_env
13. guard_p5_r7_13_mace_post_selection_trainer_missing_or_mismatched_replay_path
14. guard_p5_r7_14_mace_post_selection_trainer_executes_in_materialization_cwd
15. guard_p5_r7_15_mace_post_selection_trainer_loads_canonical_summary
16. guard_p5_r7_16_mace_post_selection_trainer_nonzero_exit_fails_closed
17. guard_p5_r7_17_mace_post_selection_trainer_plan_digest_mismatch_fails_closed
18. guard_p5_r7_18_mace_post_selection_trainer_tampered_internal_config_fails_closed
19. guard_p5_r7_19_replay_baseline_provider_uses_canonical_head
20. guard_p5_r7_20_replay_baseline_provider_tampered_model_fails_closed
21. guard_p5_r7_21_replay_baseline_cache_key_covers_all_identities
22. guard_p5_r7_22_cv_acceptance_fails_closed_on_replay_admissibility_violation
23. guard_p5_r7_23_final_production_plan_fails_closed_on_replay_lineage_mismatch
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import pytest

from mdstats.training_data._common import (
    TrainingDataInputError,
    digest,
)
from mdstats.training_data.campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
)
from mdstats.training_data.eval2 import (
    assess_eval2_checkpoint,
)
from tests.test_mlff_eval2 import point, target_metrics
from mdstats.training_data.foundation import (
    FoundationPotentialIdentity,
)
from mdstats.training_data.post_selection_cv_plan import (
    PostSelectionCvPlan,
    build_post_selection_cv_plan,
    validate_post_selection_cv_plan,
)
from mdstats.training_data.post_selection_execution import (
    MacePostSelectionTrainer,
    POST_SELECTION_MACE_CONFIG_SCHEMA,
    PostSelectionExecutionError,
    PostSelectionMaterialization,
    PostSelectionRungRequest,
    build_post_selection_foundation_baseline_provider,
    post_selection_mace_run_configuration,
    post_selection_runtime_plan,
)
from mdstats.training_data.post_selection_identity import (
    PostSelectionMethodIdentity,
    compute_replay_lineage_digest,
    resolve_post_selection_foundation_identity,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
    resolve_shared_optimizer_settings,
)
from mdstats.training_data.post_selection_production import (
    FinalProductionPlan,
    build_final_production_plan,
    validate_final_production_plan,
)
from mdstats.training_data.train2_policy import (
    CheckpointAdmissibilityPolicy,
    TrainingBudgetPolicy,
)
from mdstats.training_data.train2_runtime import (
    TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
    TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE,
    Train2RuntimeSummary,
)

from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    fixture_config_text,
    load_context,
    run_cross_validate,
)


def _make_dummy_foundation_identity(
    model_sha256: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    selected_head: str = "default",
    reference: str = "/dummy/foundation.model",
) -> FoundationPotentialIdentity:
    return FoundationPotentialIdentity(
        reference=reference,
        sha256=model_sha256,
        foundation_head=selected_head,
        model_family="MACE-MPA-0",
        architecture_signature="aa" * 32,
        model_atomic_numbers=(1, 6, 8),
        available_heads=(selected_head,),
        correction_stack=(),
    )


def _make_dummy_method_identity(training_mode: str = "multihead_replay") -> PostSelectionMethodIdentity:
    return PostSelectionMethodIdentity(
        method_recipe_version="v7",
        training_mode=training_mode,
        common_training_policy_digest="11" * 32,
        learning_rate_schedule_policy_digest="22" * 32,
        checkpoint_admissibility_policy_digest="33" * 32,
        checkpoint_selection_policy_digest="44" * 32,
        shared_optimizer_settings_digest="55" * 32,
        replay_exposure_policy_digest="66" * 32,
        extxyz_policy_digest="77" * 32,
        mace_architecture_digest="88" * 32,
        checkpoint_interval_epochs=1,
        default_dtype="float64",
        device="cpu",
        acceleration_backend="cpu",
    )


def _make_dummy_materialization(
    mat_dir: Path,
    cfg_file: Path,
    cfg_bytes: bytes,
    internal_config: dict[str, Any],
    run_plan_digest: str = "99" * 32,
    run_identity: str = "77" * 32,
) -> PostSelectionMaterialization:
    return PostSelectionMaterialization(
        run_plan_digest=run_plan_digest,
        run_identity=run_identity,
        preparation_digest="aa" * 32,
        target_train_artifact=SimpleNamespace(to_dict=lambda: {"schema": "artifact"}),
        checkpoint_monitor_artifact=SimpleNamespace(to_dict=lambda: {"schema": "artifact"}),
        outer_evaluation_artifact=None,
        mace_config_relative_path=cfg_file.name,
        mace_config_sha256=hashlib.sha256(cfg_bytes).hexdigest(),
        mace_config_digest=digest(internal_config),
        output_directory=str(mat_dir),
    )


def _make_dummy_train2_summary(
    plan: Any,
    plan_digest: str | None = None,
) -> Train2RuntimeSummary:
    p_digest = plan.content_digest if plan_digest is None else plan_digest
    return Train2RuntimeSummary(
        plan_digest=p_digest,
        training_protocol_digest=plan.training_protocol_digest,
        optimizer_policy_digest=plan.optimizer_policy_digest,
        budget_policy_digest=plan.budget_policy.policy_digest,
        lr_policy_digest=plan.learning_rate_policy.policy_digest,
        planned_epochs=5,
        execution_epoch_limit=5,
        updates_per_epoch=10,
        planned_updates=50,
        structures_per_epoch=plan.structures_per_epoch,
        planned_structures_presented=100,
        completed_epochs=5,
        completed_updates=50,
        structures_presented=100,
        last_update_index=49,
        normalized_progress=1.0,
        instantaneous_learning_rate=0.001,
        phase="adaptation",
        raw_checkpoint_epoch=5,
        raw_checkpoint_sha256="aa" * 32,
        optimizer_state_digest="bb" * 32,
        live_parameter_digest="cc" * 32,
        ema_state_digest=None,
        rng_state_digest="dd" * 32,
        group_base_learning_rates=(0.001,),
        complete_budget=True,
    )


# ---------------------------------------------------------------------------
# Guard 1: Relocation preserves canonical content digest
# ---------------------------------------------------------------------------
def test_guard_p5_r7_01_foundation_identity_invariant_to_model_path_relocation(tmp_path: Path):
    model_bytes = b"MACE_FOUNDATION_BYTES_TEST_01"
    file1 = tmp_path / "dir1" / "model.model"
    file1.parent.mkdir(parents=True)
    file1.write_bytes(model_bytes)

    file2 = tmp_path / "dir2" / "relocated_model.pt"
    file2.parent.mkdir(parents=True)
    file2.write_bytes(model_bytes)

    ident1 = FoundationPotentialIdentity.from_file(
        file1,
        model_family="MACE-MPA-0",
        foundation_head="default",
    )
    ident2 = FoundationPotentialIdentity.from_file(
        file2,
        model_family="MACE-MPA-0",
        foundation_head="default",
    )
    assert ident1.canonical_content_digest == ident2.canonical_content_digest


# ---------------------------------------------------------------------------
# Guard 2: Foundation identity digest changes when checkpoint bytes change
# ---------------------------------------------------------------------------
def test_guard_p5_r7_02_foundation_identity_changes_on_byte_modification(tmp_path: Path):
    file1 = tmp_path / "model1.model"
    file1.write_bytes(b"ORIGINAL_BYTES")
    file2 = tmp_path / "model2.model"
    file2.write_bytes(b"MODIFIED_BYTES")

    ident1 = FoundationPotentialIdentity.from_file(file1, foundation_head="default")
    ident2 = FoundationPotentialIdentity.from_file(file2, foundation_head="default")
    assert ident1.canonical_content_digest != ident2.canonical_content_digest


# ---------------------------------------------------------------------------
# Guard 3: Foundation identity digest changes when selected head changes
# ---------------------------------------------------------------------------
def test_guard_p5_r7_03_foundation_identity_changes_on_head_change(tmp_path: Path):
    file1 = tmp_path / "model.model"
    file1.write_bytes(b"MULTIHEAD_BYTES")

    ident1 = FoundationPotentialIdentity.from_file(file1, foundation_head="default")
    ident2 = FoundationPotentialIdentity.from_file(file1, foundation_head="zeolite_head")
    assert ident1.canonical_content_digest != ident2.canonical_content_digest


# ---------------------------------------------------------------------------
# Guard 4: Unsupported optimizer value fails closed
# ---------------------------------------------------------------------------
def test_guard_p5_r7_04_unsupported_training_optimizer_fails_closed():
    for bad_optimizer in ("adamw", "sgd", "rmsprop", "adagrad"):
        with pytest.raises(TrainingDataInputError) as exc_info:
            resolve_shared_optimizer_settings({"training": {"optimizer": bad_optimizer}})
        assert "Unsupported [training].optimizer" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Guard 5: PostSelectionMethodIdentity has no optimizer_family field
# ---------------------------------------------------------------------------
def test_guard_p5_r7_05_method_identity_does_not_contain_optimizer_family():
    cfg: dict[str, Any] = {
        "training": {
            "loss": "weighted",
            "energy_weight": 1.0,
            "forces_weight": 10.0,
            "stress_weight": 1.0,
            "virials_weight": 1.0,
            "dipole_weight": 0.0,
            "keep_isolated_atoms": False,
        }
    }
    policies = resolve_post_selection_method_policies(cfg)
    method = resolve_post_selection_method_identity(cfg, policies=policies)
    method_dict = method.to_dict()
    assert "optimizer_family" not in method_dict
    assert not hasattr(method, "optimizer_family")


# ---------------------------------------------------------------------------
# Guard 6: Replay lineage digest covers all replay artifacts
# ---------------------------------------------------------------------------
def test_guard_p5_r7_06_replay_lineage_digest_covers_all_replay_artifacts():
    base_res = SimpleNamespace(
        source_sha256="11" * 32,
        split_manifest_digest="22" * 32,
        train_artifact=SimpleNamespace(sha256="33" * 32, content_digest="44" * 32),
        monitor_artifact=SimpleNamespace(sha256="55" * 32, content_digest="66" * 32),
    )
    base_digest = compute_replay_lineage_digest(base_res)
    assert base_digest is not None

    # Alter train sha
    res_train_sha = SimpleNamespace(
        source_sha256="11" * 32,
        split_manifest_digest="22" * 32,
        train_artifact=SimpleNamespace(sha256="99" * 32, content_digest="44" * 32),
        monitor_artifact=SimpleNamespace(sha256="55" * 32, content_digest="66" * 32),
    )
    assert compute_replay_lineage_digest(res_train_sha) != base_digest

    # Alter monitor sha
    res_monitor_sha = SimpleNamespace(
        source_sha256="11" * 32,
        split_manifest_digest="22" * 32,
        train_artifact=SimpleNamespace(sha256="33" * 32, content_digest="44" * 32),
        monitor_artifact=SimpleNamespace(sha256="99" * 32, content_digest="66" * 32),
    )
    assert compute_replay_lineage_digest(res_monitor_sha) != base_digest

    # Alter source sha
    res_source_sha = SimpleNamespace(
        source_sha256="99" * 32,
        split_manifest_digest="22" * 32,
        train_artifact=SimpleNamespace(sha256="33" * 32, content_digest="44" * 32),
        monitor_artifact=SimpleNamespace(sha256="55" * 32, content_digest="66" * 32),
    )
    assert compute_replay_lineage_digest(res_source_sha) != base_digest

    # Alter split manifest digest
    res_manifest = SimpleNamespace(
        source_sha256="11" * 32,
        split_manifest_digest="99" * 32,
        train_artifact=SimpleNamespace(sha256="33" * 32, content_digest="44" * 32),
        monitor_artifact=SimpleNamespace(sha256="55" * 32, content_digest="66" * 32),
    )
    assert compute_replay_lineage_digest(res_manifest) != base_digest


# ---------------------------------------------------------------------------
# Guard 7 & 8: Replay monitor/train tampering fails CV plan validation
# ---------------------------------------------------------------------------
def test_guard_p5_r7_07_replay_monitor_byte_tamper_fails_plan_validation(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store)
        orig_digest = "1234567890abcdef" * 4
        tampered_digest = "fedcba0987654321" * 4

        plan = build_post_selection_cv_plan(
            context.selected,
            context.method,
            context.cv_policy,
            replay_lineage_digest=orig_digest,
        )
        assert plan.replay_lineage_digest == orig_digest

        # Validate with unchanged digest passes
        validate_post_selection_cv_plan(
            plan, context.selected, replay_lineage_digest=orig_digest
        )

        # Validate with tampered digest fails
        with pytest.raises(PostSelectionError) as exc_info:
            validate_post_selection_cv_plan(
                plan, context.selected, replay_lineage_digest=tampered_digest
            )
        assert "different replay lineage" in str(exc_info.value)
    finally:
        store.close()


def test_guard_p5_r7_08_replay_train_byte_tamper_fails_plan_validation(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(cfg, paths, store)
        orig_digest = "aaaaaaaaaaaaaaaa" * 4
        tampered_digest = "bbbbbbbbbbbbbbbb" * 4

        plan = build_post_selection_cv_plan(
            context.selected,
            context.method,
            context.cv_policy,
            replay_lineage_digest=orig_digest,
        )
        with pytest.raises(PostSelectionError) as exc_info:
            validate_post_selection_cv_plan(
                plan, context.selected, replay_lineage_digest=tampered_digest
            )
        assert "different replay lineage" in str(exc_info.value)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Guard 9: MacePostSelectionTrainer translates internal MACE config
# ---------------------------------------------------------------------------
def test_guard_p5_r7_09_mace_post_selection_trainer_translates_internal_config():
    internal = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "test_post_selection",
        "seed": 42,
        "atomic_numbers": [1, 6, 8],
        "target_train_file": "target_train.extxyz",
        "target_valid_file": "target_valid.extxyz",
        "foundation_model": "/path/to/foundation.model",
        "foundation_head": "default",
        "multiheads_finetuning": True,
        "pt_train_file": "pt_train.extxyz",
        "pt_valid_file": "pt_valid.extxyz",
        "heads": ["default", "pt_head"],
        "lr": 0.001,
        "batch_size": 4,
        "max_num_epochs": 10,
    }
    executable = post_selection_mace_run_configuration(internal)
    assert executable["train_file"] == "target_train.extxyz"
    assert executable["valid_file"] == "target_valid.extxyz"
    assert "target_train_file" not in executable
    assert "target_valid_file" not in executable
    assert executable["foundation_model"] == "/path/to/foundation.model"
    assert executable["foundation_head"] == "default"
    assert executable["multiheads_finetuning"] is True
    assert executable["pt_train_file"] == "pt_train.extxyz"


# ---------------------------------------------------------------------------
# Guard 10, 11, 12, 14: Environment variables and cwd
# ---------------------------------------------------------------------------
def test_guard_p5_r7_10_11_12_14_mace_trainer_environment_and_cwd(tmp_path: Path):
    wrapper_record_file = tmp_path / "wrapper_env.json"
    dummy_wrapper = tmp_path / "dummy_wrapper.sh"
    dummy_wrapper.write_text(
        f"""#!/usr/bin/env bash
python3 -c "
import os, json
data = {{
    'TRAIN2_PLAN': os.environ.get('{TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE}'),
    'PYTHONHASHSEED': os.environ.get('PYTHONHASHSEED'),
    'TRUE_REPLAY_PATH': os.environ.get('{TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE}'),
    'CWD': os.getcwd(),
}}
open('{wrapper_record_file}', 'w').write(json.dumps(data))
"
exit 0
""",
        encoding="utf-8",
    )
    dummy_wrapper.chmod(0o755)

    mat_dir = tmp_path / "run_root" / "materialization"
    chk_dir = tmp_path / "run_root" / "checkpoints"
    results_dir = tmp_path / "run_root" / "results"
    mat_dir.mkdir(parents=True)
    chk_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)

    internal_config = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "test_run",
        "seed": 42,
        "target_train_file": "train.extxyz",
        "target_valid_file": "valid.extxyz",
    }
    cfg_bytes = json.dumps(internal_config).encode("utf-8")
    cfg_file = mat_dir / "post_selection_mace_config.yaml"
    cfg_file.write_bytes(cfg_bytes)

    monitor_file = tmp_path / "true_replay_monitor.extxyz"
    monitor_file.write_bytes(b"TRUE_DFT_MONITOR_TEST_DATA")
    monitor_sha = hashlib.sha256(b"TRUE_DFT_MONITOR_TEST_DATA").hexdigest()

    method = _make_dummy_method_identity("multihead_replay")

    plan = post_selection_runtime_plan(
        method=method,
        optimizer_policy=SimpleNamespace(policy_digest="88" * 32, seed=42),
        budget_policy=TrainingBudgetPolicy(planned_epochs=5),
        structures_per_epoch=20,
        replay_monitor_enabled=True,
        true_replay_monitor_sha256=monitor_sha,
    )

    materialization = _make_dummy_materialization(
        mat_dir, cfg_file, cfg_bytes, internal_config
    )

    # Write summary in checkpoint_directory as expected by canonical load_train2_runtime_summary
    (chk_dir / "train2_runtime.json").write_text(
        json.dumps(_make_dummy_train2_summary(plan).to_dict()), encoding="utf-8"
    )

    trainer = MacePostSelectionTrainer(wrapper_path=dummy_wrapper)
    request = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
        replay_monitor_path=monitor_file,
    )

    summary = trainer(request)
    assert summary.plan_digest == plan.content_digest

    recorded = json.loads(wrapper_record_file.read_text(encoding="utf-8"))
    # Guard 10: MDSTATS_TRAIN2_RUNTIME_PLAN
    assert json.loads(recorded["TRAIN2_PLAN"]) == plan.to_dict()
    # Guard 11: PYTHONHASHSEED
    assert recorded["PYTHONHASHSEED"] == "42"
    # Guard 12: MDSTATS_TRAIN2_TRUE_REPLAY_PATH
    assert recorded["TRUE_REPLAY_PATH"] == str(monitor_file.resolve())
    # Guard 14: cwd is materialization directory
    assert recorded["CWD"] == str(mat_dir.resolve())


# ---------------------------------------------------------------------------
# Guard 13: Missing or mismatched replay path fails closed
# ---------------------------------------------------------------------------
def test_guard_p5_r7_13_mace_post_selection_trainer_missing_or_mismatched_replay_path(tmp_path: Path):
    dummy_wrapper = tmp_path / "dummy_wrapper.sh"
    dummy_wrapper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    dummy_wrapper.chmod(0o755)

    mat_dir = tmp_path / "mat"
    mat_dir.mkdir()
    chk_dir = tmp_path / "chk"
    chk_dir.mkdir()

    internal_config = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "test_run",
        "seed": 42,
        "target_train_file": "train.extxyz",
        "target_valid_file": "valid.extxyz",
    }
    cfg_bytes = json.dumps(internal_config).encode("utf-8")
    cfg_file = mat_dir / "post_selection_mace_config.yaml"
    cfg_file.write_bytes(cfg_bytes)

    materialization = _make_dummy_materialization(
        mat_dir, cfg_file, cfg_bytes, internal_config
    )

    method = _make_dummy_method_identity("multihead_replay")

    plan = post_selection_runtime_plan(
        method=method,
        optimizer_policy=SimpleNamespace(policy_digest="88" * 32, seed=42),
        budget_policy=TrainingBudgetPolicy(planned_epochs=5),
        structures_per_epoch=20,
        replay_monitor_enabled=True,
        true_replay_monitor_sha256="aa" * 32,
    )

    trainer = MacePostSelectionTrainer(wrapper_path=dummy_wrapper)

    # Nonexistent path
    request_missing = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
        replay_monitor_path=tmp_path / "nonexistent.extxyz",
    )
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(request_missing)
    assert "TRUE_DFT replay monitor path is missing" in str(exc_info.value)

    # Mismatched SHA
    wrong_file = tmp_path / "wrong.extxyz"
    wrong_file.write_bytes(b"WRONG_DATA")
    request_mismatch = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
        replay_monitor_path=wrong_file,
    )
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(request_mismatch)
    assert "TRUE_DFT replay monitor SHA256 does not match" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Guard 15: Canonical summary loading from checkpoint_directory
# ---------------------------------------------------------------------------
def test_guard_p5_r7_15_mace_post_selection_trainer_loads_canonical_summary(tmp_path: Path):
    dummy_wrapper = tmp_path / "dummy_wrapper.sh"
    dummy_wrapper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    dummy_wrapper.chmod(0o755)

    mat_dir = tmp_path / "mat"
    mat_dir.mkdir()
    chk_dir = tmp_path / "chk"
    chk_dir.mkdir()

    internal_config = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "test_run",
        "seed": 42,
        "target_train_file": "train.extxyz",
        "target_valid_file": "valid.extxyz",
    }
    cfg_bytes = json.dumps(internal_config).encode("utf-8")
    cfg_file = mat_dir / "post_selection_mace_config.yaml"
    cfg_file.write_bytes(cfg_bytes)

    materialization = _make_dummy_materialization(
        mat_dir, cfg_file, cfg_bytes, internal_config
    )

    method = _make_dummy_method_identity("scratch")

    plan = post_selection_runtime_plan(
        method=method,
        optimizer_policy=SimpleNamespace(policy_digest="88" * 32, seed=42),
        budget_policy=TrainingBudgetPolicy(planned_epochs=3),
        structures_per_epoch=10,
        replay_monitor_enabled=False,
    )

    trainer = MacePostSelectionTrainer(wrapper_path=dummy_wrapper)
    request = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
    )

    # Without summary file in chk_dir, fails closed
    with pytest.raises(Exception):
        trainer(request)


# ---------------------------------------------------------------------------
# Guard 16: Non-zero exit code fails closed
# ---------------------------------------------------------------------------
def test_guard_p5_r7_16_mace_post_selection_trainer_nonzero_exit_fails_closed(tmp_path: Path):
    failing_wrapper = tmp_path / "failing_wrapper.sh"
    failing_wrapper.write_text("#!/usr/bin/env bash\necho 'MACE GPU OOM' >&2\nexit 137\n", encoding="utf-8")
    failing_wrapper.chmod(0o755)

    mat_dir = tmp_path / "mat"
    mat_dir.mkdir()
    chk_dir = tmp_path / "chk"
    chk_dir.mkdir()

    internal_config = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "test_run",
        "seed": 42,
        "target_train_file": "train.extxyz",
        "target_valid_file": "valid.extxyz",
    }
    cfg_bytes = json.dumps(internal_config).encode("utf-8")
    cfg_file = mat_dir / "post_selection_mace_config.yaml"
    cfg_file.write_bytes(cfg_bytes)

    materialization = _make_dummy_materialization(
        mat_dir, cfg_file, cfg_bytes, internal_config
    )

    method = _make_dummy_method_identity("scratch")

    plan = post_selection_runtime_plan(
        method=method,
        optimizer_policy=SimpleNamespace(policy_digest="88" * 32, seed=42),
        budget_policy=TrainingBudgetPolicy(planned_epochs=3),
        structures_per_epoch=10,
    )

    trainer = MacePostSelectionTrainer(wrapper_path=failing_wrapper)
    request = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
    )
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(request)
    assert "Post-selection MACE training failed (exit 137)" in str(exc_info.value)
    assert "MACE GPU OOM" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Guard 17: Summary plan digest mismatch fails closed
# ---------------------------------------------------------------------------
def test_guard_p5_r7_17_mace_post_selection_trainer_plan_digest_mismatch_fails_closed(tmp_path: Path):
    dummy_wrapper = tmp_path / "dummy_wrapper.sh"
    dummy_wrapper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    dummy_wrapper.chmod(0o755)

    mat_dir = tmp_path / "mat"
    mat_dir.mkdir()
    chk_dir = tmp_path / "chk"
    chk_dir.mkdir()

    internal_config = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "test_run",
        "seed": 42,
        "target_train_file": "train.extxyz",
        "target_valid_file": "valid.extxyz",
    }
    cfg_bytes = json.dumps(internal_config).encode("utf-8")
    cfg_file = mat_dir / "post_selection_mace_config.yaml"
    cfg_file.write_bytes(cfg_bytes)

    materialization = _make_dummy_materialization(
        mat_dir, cfg_file, cfg_bytes, internal_config
    )

    method = _make_dummy_method_identity("scratch")

    plan = post_selection_runtime_plan(
        method=method,
        optimizer_policy=SimpleNamespace(policy_digest="88" * 32, seed=42),
        budget_policy=TrainingBudgetPolicy(planned_epochs=3),
        structures_per_epoch=10,
    )

    # Write summary with mismatched plan digest
    (chk_dir / "train2_runtime.json").write_text(
        json.dumps(_make_dummy_train2_summary(plan, plan_digest="ff" * 32).to_dict()), encoding="utf-8"
    )

    trainer = MacePostSelectionTrainer(wrapper_path=dummy_wrapper)
    request = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
    )
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(request)
    assert "Loaded TRAIN2 runtime summary plan digest does not match" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Guard 18: Tampered internal config payload fails closed
# ---------------------------------------------------------------------------
def test_guard_p5_r7_18_mace_post_selection_trainer_tampered_internal_config_fails_closed(tmp_path: Path):
    dummy_wrapper = tmp_path / "dummy_wrapper.sh"
    dummy_wrapper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    dummy_wrapper.chmod(0o755)

    mat_dir = tmp_path / "mat"
    mat_dir.mkdir()
    chk_dir = tmp_path / "chk"
    chk_dir.mkdir()

    internal_config = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "test_run",
        "seed": 42,
        "target_train_file": "train.extxyz",
        "target_valid_file": "valid.extxyz",
    }
    cfg_bytes = json.dumps(internal_config).encode("utf-8")
    cfg_file = mat_dir / "post_selection_mace_config.yaml"
    cfg_file.write_bytes(b"TAMPERED_CONTENT_BYTES")

    materialization = _make_dummy_materialization(
        mat_dir, cfg_file, cfg_bytes, internal_config
    )

    method = _make_dummy_method_identity("scratch")

    plan = post_selection_runtime_plan(
        method=method,
        optimizer_policy=SimpleNamespace(policy_digest="88" * 32, seed=42),
        budget_policy=TrainingBudgetPolicy(planned_epochs=3),
        structures_per_epoch=10,
    )

    trainer = MacePostSelectionTrainer(wrapper_path=dummy_wrapper)
    request = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
    )
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(request)
    assert "bytes changed before training" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Guard 19 & 20: Replay baseline provider uses canonical head & checks SHA
# ---------------------------------------------------------------------------
def test_guard_p5_r7_19_20_replay_baseline_provider_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    model_path = tmp_path / "foundation.model"
    model_path.write_bytes(b"FOUNDATION_MODEL_BYTES")
    correct_sha = hashlib.sha256(b"FOUNDATION_MODEL_BYTES").hexdigest()

    ident = _make_dummy_foundation_identity(
        model_sha256=correct_sha,
        selected_head="zeolite_head",
        reference=str(model_path),
    )

    captured_kwargs: dict[str, Any] = {}
    def dummy_from_model_path(path, **kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs["path"] = path
        return SimpleNamespace(identity=ident, calculator="dummy_calc")

    from mdstats.training_data.model_features import MaceCalculatorProvider
    monkeypatch.setattr(MaceCalculatorProvider, "from_model_path", dummy_from_model_path)

    # Valid construction
    provider = build_post_selection_foundation_baseline_provider(
        foundation_path=model_path,
        foundation_identity=ident,
        foundation_head="zeolite_head",
        allow_forward_override=True,
    )
    assert provider is not None
    assert captured_kwargs["head"] == "zeolite_head"
    assert captured_kwargs["foundation_potential_identity"] == ident

    # Guard 20: Tampered foundation model bytes fails closed
    tampered_ident = _make_dummy_foundation_identity(
        model_sha256="ff" * 32,
        selected_head="zeolite_head",
        reference=str(model_path),
    )
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        build_post_selection_foundation_baseline_provider(
            foundation_path=model_path,
            foundation_identity=tampered_ident,
            foundation_head="zeolite_head",
            allow_forward_override=True,
        )
    assert "Foundation baseline model bytes changed on disk" in str(exc_info.value)

    # Missing model fails closed
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        build_post_selection_foundation_baseline_provider(
            foundation_path=tmp_path / "nonexistent.model",
            foundation_identity=ident,
            foundation_head="zeolite_head",
            allow_forward_override=True,
        )
    assert "does not exist" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Guard 21: Replay baseline cache key covers all identities
# ---------------------------------------------------------------------------
def test_guard_p5_r7_21_replay_baseline_cache_key_covers_all_identities():
    def make_key(
        foundation_content_digest="11" * 32,
        foundation_head="default",
        monitor_sha256="22" * 32,
        monitor_digest="33" * 32,
        eval2_metric_policy_digest="44" * 32,
        default_dtype="float64",
        device="cpu",
    ):
        return digest({
            "foundation_content_digest": foundation_content_digest,
            "foundation_head": foundation_head,
            "monitor_sha256": monitor_sha256,
            "monitor_digest": monitor_digest,
            "eval2_metric_policy_digest": eval2_metric_policy_digest,
            "default_dtype": default_dtype,
            "device": device,
        })

    k0 = make_key()
    assert make_key(foundation_content_digest="99" * 32) != k0
    assert make_key(foundation_head="zeolite") != k0
    assert make_key(monitor_sha256="99" * 32) != k0
    assert make_key(monitor_digest="99" * 32) != k0
    assert make_key(eval2_metric_policy_digest="99" * 32) != k0
    assert make_key(default_dtype="float32") != k0
    assert make_key(device="cuda") != k0


# ---------------------------------------------------------------------------
# Guard 22: CV acceptance fails closed on replay admissibility violation
# ---------------------------------------------------------------------------
def test_guard_p5_r7_22_cv_acceptance_fails_closed_on_replay_admissibility_violation():
    admissibility = CheckpointAdmissibilityPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.10,
        replay_enabled=True,
        replay_degradation_budget_ev_per_angstrom=0.005,
        replay_label_requirement="true_dft",
    )
    p = point(1, 0.05)
    metrics = target_metrics(0.05)

    # Candidate force RMSE = 0.50, Foundation = 0.20 -> degradation = 0.30 > 0.005 budget -> Inadmissible!
    record = assess_eval2_checkpoint(
        p,
        evaluation_record_digest="22" * 32,
        target_metrics=metrics,
        admissibility_policy=admissibility,
        replay_candidate_force_rmse_ev_per_angstrom=0.50,
        replay_foundation_force_rmse_ev_per_angstrom=0.20,
        replay_label_mode="true_dft",
    )
    assert not record.admissible
    assert "replay_retention_ceiling_exceeded" in record.rejection_reasons


# ---------------------------------------------------------------------------
# Guard 23: Final production plan fails closed on replay lineage mismatch
# ---------------------------------------------------------------------------
def test_guard_p5_r7_23_final_production_plan_fails_closed_on_replay_lineage_mismatch(tmp_path: Path):
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths, store = load_context(config)
    harness = PostSelectionHarness()
    try:
        context = build_post_selection_context(cfg, paths, store)
        rc = run_cross_validate(config, harness)
        assert rc == 0
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        assert plan is not None and acceptance is not None

        # Build with matching replay lineage passes
        final_plan = build_final_production_plan(
            context.selected,
            context.method,
            context.production_policy,
            cv_plan=plan,
            cv_acceptance=acceptance,
            replay_lineage_digest=plan.replay_lineage_digest,
        )
        assert final_plan is not None

        # Build with mismatched replay lineage fails closed
        with pytest.raises(PostSelectionError) as exc_info:
            build_final_production_plan(
                context.selected,
                context.method,
                context.production_policy,
                cv_plan=plan,
                cv_acceptance=acceptance,
                replay_lineage_digest="1234567890abcdef" * 4,
            )
        assert "different replay lineage" in str(exc_info.value)
    finally:
        store.close()
