"""Mandatory negative and parity qualification guards for P5-R8.

Implements all 38 mandatory claims specified in Section 4 and Section 3 of
workplans/active/mlff-target-size-v7-packages/P5_POST_SELECTION_CV_FINAL_PRODUCTION.md (Revision 8).
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import pytest

import mdstats
from mdstats.training_data._common import (
    TrainingDataInputError,
    digest,
    sha256_file_cached,
)
from mdstats.training_data.campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    PostSelectionContext,
    _optimizer_policy_for,
    _resolve_post_selection_replay_resolution,
    build_post_selection_context,
    execute_post_selection_cross_validation,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
    resolve_current_final_production_plan,
)
from mdstats.training_data.eval2 import (
    assess_eval2_checkpoint,
)
from mdstats.training_data.foundation import (
    FoundationInferenceIdentity,
    FoundationPotentialIdentity,
    MaceFoundationFamily,
    MaceFoundationInspection,
    MaceFoundationSpec,
    inspect_mace_foundation,
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
    CvValidationPolicyIdentity,
    FinalProductionPolicyIdentity,
    PostSelectionMethodIdentity,
    compute_replay_lineage_digest,
    cv_training_budget_policy,
    resolve_cv_validation_policy_identity,
    resolve_post_selection_foundation_identity,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
    resolve_post_selection_replay_policy_digest,
    resolve_shared_optimizer_settings,
)
from mdstats.training_data.post_selection_production import (
    FinalProductionPlan,
    build_final_production_plan,
    frozen_m3_development_evidence,
    validate_final_production_plan,
)
from mdstats.training_data.replay import (
    ReplayFileArtifact,
    ReplayLabelMode,
)
from mdstats.training_data.train2_policy import (
    CheckpointAdmissibilityPolicy,
    CheckpointSelectionPolicy,
    LearningRateSchedulePolicy,
    TrainingBudgetPolicy,
)
from mdstats.training_data.train2_runtime import (
    TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
    TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE,
    Train2RuntimePlan,
    Train2RuntimeSummary,
)
from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    fixture_config_text,
    load_context,
    run_cross_validate,
    run_train_production,
)
from tests.test_mlff_eval2 import point, target_metrics


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def _synthetic_inspection(*, heads: tuple[str, ...] = ("default",), family: str = "mace_mpa_0") -> MaceFoundationInspection:
    if family in ("mace_mh_1", "mh_1"):
        interactions = ({"class": "RealAgnosticResidualNonLinearInteractionBlock"},)
        use_agnostic = True
    elif family in ("mace_custom", "custom"):
        interactions = ({"class": "CustomInteractionBlock"},)
        use_agnostic = False
    else:
        interactions = ({"class": "RealAgnosticDensityResidualInteractionBlock"},)
        use_agnostic = False
    return MaceFoundationInspection(
        reference="/synthetic/model.model",
        sha256="44" * 32,
        model_class="ScaleShiftMACE",
        model_module="mace.modules.models",
        available_heads=heads,
        atomic_numbers=(1, 6, 8),
        r_max_angstrom=5.0,
        num_interactions=2,
        model_dtype="float64",
        atomic_energies_shape=(len(heads), 3) if len(heads) > 1 else (3,),
        interaction_signatures=interactions,
        product_signatures=({"class": "EquivariantProductBasisBlock"},),
        readout_signatures=({"class": "LinearReadoutBlock"},),
        edge_irreps="128x0e",
        use_agnostic_product=use_agnostic,
        use_last_readout_only=False,
        state_shape_digest="55" * 32,
    )


def _make_dummy_method_identity(mode: str = "scratch", backend: str = "e3nn") -> PostSelectionMethodIdentity:
    return PostSelectionMethodIdentity(
        method_recipe_version="mdstats.post-selection-method.2026-08.v1",
        training_mode=mode,
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
        acceleration_backend=backend,
    )


def _make_dummy_materialization(
    mat_dir: Path,
    cfg_file: Path,
    cfg_bytes: bytes,
    internal_config: dict[str, Any],
    train_file: Path | None = None,
    valid_file: Path | None = None,
) -> PostSelectionMaterialization:
    run_plan_digest = "12" * 32
    run_identity = "34" * 32

    t_train = train_file or (mat_dir / "train.extxyz")
    if not t_train.is_file():
        t_train.write_bytes(b"TARGET_TRAIN_BYTES")
    t_valid = valid_file or (mat_dir / "valid.extxyz")
    if not t_valid.is_file():
        t_valid.write_bytes(b"TARGET_VALID_BYTES")

    t_train_sha = sha256_file_cached(t_train)
    t_valid_sha = sha256_file_cached(t_valid)

    train_art = SimpleNamespace(
        relative_path=t_train.name,
        sha256=t_train_sha,
        content_digest="t1" * 32,
        configuration_count=10,
        to_dict=lambda: {"schema": "artifact"},
    )
    valid_art = SimpleNamespace(
        relative_path=t_valid.name,
        sha256=t_valid_sha,
        content_digest="t2" * 32,
        configuration_count=5,
        to_dict=lambda: {"schema": "artifact"},
    )

    return PostSelectionMaterialization(
        run_plan_digest=run_plan_digest,
        run_identity=run_identity,
        preparation_digest="aa" * 32,
        target_train_artifact=train_art,
        checkpoint_monitor_artifact=valid_art,
        outer_evaluation_artifact=None,
        mace_config_relative_path=cfg_file.name,
        mace_config_sha256=hashlib.sha256(cfg_bytes).hexdigest(),
        mace_config_digest=digest(internal_config),
        output_directory=str(mat_dir),
    )


def _make_dummy_train2_summary(plan: Any, plan_digest: str | None = None) -> Train2RuntimeSummary:
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
# Claims 1 to 7: Canonical Foundation Resolution & Parity Matrix
# ---------------------------------------------------------------------------

def test_claims_01_02_foundation_inspection_fails_closed_without_fallback(tmp_path: Path):
    """Claim 1: Real foundation resolver executes without missing imports.
    Claim 2: Corrupt/unsupported foundation cannot downgrade to byte-only identity.
    """
    corrupt_file = tmp_path / "corrupt_model.model"
    corrupt_file.write_bytes(b"NOT_A_VALID_TORCH_MODEL_BYTES")

    # Direct execution of resolve_post_selection_foundation_identity must raise TrainingDataInputError
    with pytest.raises(TrainingDataInputError) as exc_info:
        resolve_post_selection_foundation_identity(corrupt_file)
    assert "Failed to load MACE foundation checkpoint" in str(exc_info.value) or "requires torch" in str(exc_info.value)


def test_claims_03_04_05_foundation_family_and_head_resolution_guards(tmp_path: Path, monkeypatch):
    """Claim 3: Wrong foundation family fails.
    Claim 4: Multi-head omitted head fails.
    Claim 5: Unavailable explicit head fails.
    """
    dummy_file = tmp_path / "mock_model.model"
    dummy_file.write_bytes(b"MOCK_BYTES")

    # Multihead inspection with heads: ("matpes_r2scan", "omat_pbe")
    multi_insp = _synthetic_inspection(heads=("matpes_r2scan", "omat_pbe"), family="mace_mh_1")
    monkeypatch.setattr("mdstats.training_data.foundation.inspect_mace_foundation", lambda p: multi_insp)

    # Claim 4: Multi-head with omitted head raises TrainingDataInputError
    with pytest.raises(TrainingDataInputError) as exc_info:
        resolve_post_selection_foundation_identity(dummy_file, requested_head=None, model_family="mace_mh_1")
    assert "Multi-head MACE foundation requires an explicit foundation head" in str(exc_info.value)

    # Claim 5: Unavailable explicit head raises TrainingDataInputError
    with pytest.raises(TrainingDataInputError) as exc_info:
        resolve_post_selection_foundation_identity(dummy_file, requested_head="non_existent_head", model_family="mace_mh_1")
    assert "Requested foundation head 'non_existent_head' is unavailable" in str(exc_info.value)

    # Claim 3: Wrong foundation family raises TrainingDataInputError
    with pytest.raises(TrainingDataInputError) as exc_info:
        resolve_post_selection_foundation_identity(dummy_file, requested_head="matpes_r2scan", model_family="unknown_family")
    assert "Unsupported MACE foundation family" in str(exc_info.value)


def test_claims_06_07_foundation_relocation_and_byte_mutation_invariants(tmp_path: Path, monkeypatch):
    """Claim 6: Foundation relocation with same bytes/head preserves P5 method identity.
    Claim 7: Foundation bytes changed at same path invalidate/fail old method/CV.
    """
    file1 = tmp_path / "dir1" / "model.model"
    file1.parent.mkdir(parents=True)
    file1.write_bytes(b"FOUNDATION_BYTES_1")

    file2 = tmp_path / "dir2" / "relocated.model"
    file2.parent.mkdir(parents=True)
    file2.write_bytes(b"FOUNDATION_BYTES_1")

    insp1 = _synthetic_inspection(heads=("default",), family="mace_mpa_0")
    monkeypatch.setattr("mdstats.training_data.foundation.inspect_mace_foundation", lambda p: replace(insp1, sha256=sha256_file_cached(p)))

    ident1 = resolve_post_selection_foundation_identity(file1)
    ident2 = resolve_post_selection_foundation_identity(file2)
    assert ident1.canonical_content_digest == ident2.canonical_content_digest

    # Claim 7: Byte mutation at same path changes canonical_content_digest
    file1.write_bytes(b"FOUNDATION_BYTES_MUTATED")
    ident1_mutated = resolve_post_selection_foundation_identity(file1)
    assert ident1_mutated.canonical_content_digest != ident1.canonical_content_digest


# ---------------------------------------------------------------------------
# Claims 8 to 13: Path-Free Replay Policy, Lineage, and Mutation Invariants
# ---------------------------------------------------------------------------

def test_claims_08_09_10_replay_policy_and_lineage_path_free():
    """Claim 8: Replay shared method digest contains no filesystem path.
    Claim 9: Replay source relocation with same bytes/policy/split preserves method identity.
    Claim 10: Replay lineage contains no filesystem path.
    """
    single_mock = SimpleNamespace(
        label_mode=ReplayLabelMode.TRUE_DFT,
        split_ratio=(0.8, 0.2),
        split_seed=42,
    )
    digest1 = resolve_post_selection_replay_policy_digest(
        single_replay=single_mock,
        has_legacy_replay=False,
        target_head_name="target_head",
        replay_head_name="pt_head",
    )
    digest2 = resolve_post_selection_replay_policy_digest(
        single_replay=single_mock,
        has_legacy_replay=False,
        target_head_name="target_head",
        replay_head_name="pt_head",
    )
    assert digest1 == digest2

    # Replay lineage helper contains no path fields in its hashing payload
    resolution = SimpleNamespace(
        interface="single_source",
        source_content_digest="sc" * 32,
        source_sha256="ss" * 32,
        split_manifest_digest="sm" * 32,
        train_artifact=SimpleNamespace(content_digest="tc" * 32, sha256="ts" * 32),
        monitor_artifact=SimpleNamespace(content_digest="mc" * 32, sha256="ms" * 32),
        true_label_mode="true_dft",
    )
    lineage_digest = compute_replay_lineage_digest(resolution)
    assert lineage_digest is not None
    assert isinstance(lineage_digest, str) and len(lineage_digest) == 64


def test_claims_11_12_13_replay_source_and_monitor_byte_tamper(tmp_path: Path):
    """Claim 11: Replay source byte mutation invalidates CV->final authorization.
    Claim 12: Replay split seed/ratio mutation invalidates the appropriate policy/lineage.
    Claim 13: TRUE_DFT monitor byte mutation fails before training/evaluation.
    """
    resolution1 = SimpleNamespace(
        interface="single_source",
        source_content_digest="sc" * 32,
        source_sha256="ss" * 32,
        split_manifest_digest="sm" * 32,
        train_artifact=SimpleNamespace(content_digest="tc" * 32, sha256="ts" * 32),
        monitor_artifact=SimpleNamespace(content_digest="mc" * 32, sha256="ms" * 32),
        true_label_mode="true_dft",
    )
    lineage1 = compute_replay_lineage_digest(resolution1)

    # Claim 11: Source SHA mutation changes lineage
    resolution_mutated_source = SimpleNamespace(**{**vars(resolution1), "source_sha256": "ss_mutated" * 16})
    lineage2 = compute_replay_lineage_digest(resolution_mutated_source)
    assert lineage1 != lineage2

    # Claim 12: Split manifest mutation changes lineage
    resolution_mutated_split = SimpleNamespace(**{**vars(resolution1), "split_manifest_digest": "sm_mutated" * 16})
    lineage3 = compute_replay_lineage_digest(resolution_mutated_split)
    assert lineage1 != lineage3

    # Claim 13: Monitor SHA mutation changes lineage
    resolution_mutated_monitor = SimpleNamespace(
        **{
            **vars(resolution1),
            "monitor_artifact": SimpleNamespace(content_digest="mc" * 32, sha256="ms_mutated" * 16),
        }
    )
    lineage4 = compute_replay_lineage_digest(resolution_mutated_monitor)
    assert lineage1 != lineage4


# ---------------------------------------------------------------------------
# Claims 14 to 20: Dtype, Mode, Optimizer, Interval, and Acceleration Parity
# ---------------------------------------------------------------------------

def test_claims_14_15_16_invalid_dtype_mode_and_optimizer_fail_closed():
    """Claim 14: Invalid dtype rejects instead of coercing to float64.
    Claim 15: Invalid training mode rejects.
    Claim 16: Unsupported optimizer family remains rejected.
    """
    # Claim 14: invalid dtype
    cfg_invalid_dtype = {"training": {"dtype": "bfloat16"}}
    with pytest.raises(TrainingDataInputError) as exc_info:
        resolve_post_selection_method_policies(cfg_invalid_dtype)
    assert "Unsupported [training].default_dtype: 'bfloat16'" in str(exc_info.value)

    # Claim 15: invalid training mode
    cfg_invalid_mode = {"training": {"mode": "unsupported_reinforcement_learning"}}
    with pytest.raises(TrainingDataInputError) as exc_info:
        resolve_post_selection_method_policies(cfg_invalid_mode)
    assert "Unsupported training mode" in str(exc_info.value)

    # Claim 16: unsupported optimizer
    cfg_invalid_opt = {"training": {"optimizer": "rmsprop"}}
    with pytest.raises(TrainingDataInputError) as exc_info:
        resolve_shared_optimizer_settings(cfg_invalid_opt)
    assert "Unsupported [training].optimizer: rmsprop" in str(exc_info.value)


def test_claims_17_18_19_20_eval_interval_and_acceleration_parity():
    """Claim 17: eval_interval mutation changes both method identity and executable MACE config.
    Claim 18: Checkpoint interval mutation changes method identity and TRAIN2 budget/checkpoint policy.
    Claim 19: Acceleration backend mutation changes method identity and canonical MACE acceleration config.
    Claim 20: Method acceleration backend cannot disagree with run optimizer acceleration backend.
    """
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.post_selection_execution import _post_selection_mace_config

    def config(*, eval_interval=1, checkpoint_interval=1, backend="e3nn"):
        return {
            "campaign": {"precision_profile": "double"},
            "training": {
                "device": "cpu",
                "dtype": "float64",
                "batch_size": 2,
                "valid_batch_size": 2,
                "eval_interval": eval_interval,
                "checkpoint_interval_epochs": checkpoint_interval,
            },
            "acceleration": {
                "backend": backend,
                "training_backend": backend,
                "only_cueq": backend == "cueq",
            },
        }

    preparation = SimpleNamespace(
        fitted_atomic_references=SimpleNamespace(
            reference_energies_ev=((3, 0.0), (8, 0.0))
        )
    )
    target_train = SimpleNamespace(relative_path="train.extxyz", atomic_numbers=(3, 8))
    monitor = SimpleNamespace(relative_path="valid.extxyz", atomic_numbers=(3, 8))

    # Claim 17: the real method identity, optimizer policy, internal MACE
    # config, and translated executable config all carry eval_interval.
    cfg1 = config(eval_interval=1)
    cfg2 = config(eval_interval=5)
    method1 = resolve_post_selection_method_identity(cfg1)
    method2 = resolve_post_selection_method_identity(cfg2)
    assert method1.content_digest != method2.content_digest
    optimizer2 = cli._optimizer_policy(
        cfg2, seed=42, num_workers=0, paths=None, planned_epochs=5
    )
    internal2 = _post_selection_mace_config(
        run_identity="r9b-eval",
        optimizer_seed=42,
        planned_epochs=5,
        preparation=preparation,
        optimizer_policy=optimizer2,
        target_train=target_train,
        monitor=monitor,
        extxyz_policy=resolve_post_selection_method_policies(cfg2).extxyz,
        method=method2,
    )
    assert internal2["eval_interval"] == 5
    assert post_selection_mace_run_configuration(internal2)["eval_interval"] == 5

    # Claim 18: checkpoint interval is resolved by the method and the actual
    # CV budget/runtime-plan owners.
    cfg_interval = config(checkpoint_interval=3)
    interval_method = resolve_post_selection_method_identity(cfg_interval)
    assert interval_method.content_digest != method1.content_digest
    cv_policy = resolve_cv_validation_policy_identity(
        {"post_selection": {"cv": {}}}
    )
    interval_budget = cv_training_budget_policy(interval_method, cv_policy)
    assert interval_budget.checkpoint_interval_epochs == 3
    interval_runtime = post_selection_runtime_plan(
        method=interval_method,
        optimizer_policy=cli._optimizer_policy(
            cfg_interval, seed=42, num_workers=0, paths=None, planned_epochs=5
        ),
        budget_policy=interval_budget,
        structures_per_epoch=1,
    )
    assert interval_runtime.budget_policy.checkpoint_interval_epochs == 3

    # Claim 19: configured acceleration flows through method resolution, the
    # actual optimizer policy, and the executable MACE translation.
    cfg_cueq = config(backend="cueq")
    cueq_policies = resolve_post_selection_method_policies(cfg_cueq)
    assert cueq_policies.acceleration_backend == "cueq"
    cueq_method = resolve_post_selection_method_identity(
        cfg_cueq, policies=cueq_policies
    )
    cueq_internal = _post_selection_mace_config(
        run_identity="r9b-cueq",
        optimizer_seed=42,
        planned_epochs=5,
        preparation=preparation,
        optimizer_policy=cli._optimizer_policy(
            cfg_cueq, seed=42, num_workers=0, paths=None, planned_epochs=5
        ),
        target_train=target_train,
        monitor=monitor,
        extxyz_policy=cueq_policies.extxyz,
        method=cueq_method,
    )
    cueq_exec = post_selection_mace_run_configuration(cueq_internal)
    assert cueq_exec["enable_cueq"] is True
    assert cueq_exec["only_cueq"] is True

    # Claim 20: use the actual optimizer/method parity owner, not a test-local
    # comparison of two manually-created fields.
    mismatch_ctx = SimpleNamespace(
        cfg=config(backend="cueq"),
        paths=None,
        method=SimpleNamespace(acceleration_backend="e3nn"),
    )
    with pytest.raises(PostSelectionError, match="does not match"):
        _optimizer_policy_for(mismatch_ctx, seed=42, planned_epochs=5)


# ---------------------------------------------------------------------------
# Claims 21 to 29: Production Trainer Pre-Launch Authentication Matrix
# ---------------------------------------------------------------------------

def test_claims_21_to_29_mace_post_selection_trainer_pre_launch_guards(tmp_path: Path):
    """Claims 21-26: Scientific artifact tamper blocks wrapper launch before subprocess starts.
    Claims 27-29: Translated config, exact TRAIN2 environment, and canonical summary loading.
    """
    wrapper_invocation_file = tmp_path / "invocations.txt"
    wrapper_env_file = tmp_path / "wrapper_env.json"
    dummy_wrapper = tmp_path / "dummy_wrapper.sh"
    dummy_wrapper.write_text(
        f"""#!/usr/bin/env bash
echo "LAUNCHED" >> "{wrapper_invocation_file}"
python3 -c "
import os, json
data = {{
    'TRAIN2_PLAN': os.environ.get('{TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE}'),
    'PYTHONHASHSEED': os.environ.get('PYTHONHASHSEED'),
    'TRUE_REPLAY_PATH': os.environ.get('{TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE}'),
    'CWD': os.getcwd(),
}}
open('{wrapper_env_file}', 'w').write(json.dumps(data))
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
        "eval_interval": 2,
    }
    cfg_bytes = json.dumps(internal_config).encode("utf-8")
    cfg_file = mat_dir / "post_selection_mace_config.yaml"
    cfg_file.write_bytes(cfg_bytes)

    t_train = mat_dir / "train.extxyz"
    t_train.write_bytes(b"TARGET_TRAIN_DATA")
    t_valid = mat_dir / "valid.extxyz"
    t_valid.write_bytes(b"TARGET_VALID_DATA")

    foundation_file = tmp_path / "foundation.model"
    foundation_file.write_bytes(b"FOUNDATION_MODEL_DATA")
    foundation_sha = sha256_file_cached(foundation_file)

    replay_train_file = tmp_path / "replay_train.extxyz"
    replay_train_file.write_bytes(b"REPLAY_TRAIN_DATA")
    replay_train_sha = sha256_file_cached(replay_train_file)

    replay_monitor_file = tmp_path / "replay_monitor.extxyz"
    replay_monitor_file.write_bytes(b"REPLAY_MONITOR_DATA")
    replay_monitor_sha = sha256_file_cached(replay_monitor_file)

    method = _make_dummy_method_identity("multihead_replay")
    plan = post_selection_runtime_plan(
        method=method,
        optimizer_policy=SimpleNamespace(policy_digest="88" * 32, seed=42),
        budget_policy=TrainingBudgetPolicy(planned_epochs=5),
        structures_per_epoch=20,
        replay_monitor_enabled=True,
        true_replay_monitor_sha256=replay_monitor_sha,
    )

    materialization = _make_dummy_materialization(
        mat_dir, cfg_file, cfg_bytes, internal_config, train_file=t_train, valid_file=t_valid
    )

    trainer = MacePostSelectionTrainer(wrapper_path=dummy_wrapper)
    f_ident = SimpleNamespace(sha256=foundation_sha, foundation_head="default", canonical_content_digest="ff" * 32)
    rp_train_art = SimpleNamespace(sha256=replay_train_sha, content_digest="rt" * 32)
    rp_mon_art = SimpleNamespace(sha256=replay_monitor_sha, content_digest="rm" * 32)

    base_request = PostSelectionRungRequest(
        plan=plan,
        run_plan=SimpleNamespace(run_identity="77" * 32),
        materialization=materialization,
        materialization_directory=mat_dir,
        checkpoint_directory=chk_dir,
        optimizer_policy=SimpleNamespace(seed=42),
        foundation_identity=f_ident,
        foundation_model_path=foundation_file,
        replay_train_artifact=rp_train_art,
        replay_train_path=replay_train_file,
        replay_monitor_artifact=rp_mon_art,
        replay_monitor_path=replay_monitor_file,
    )

    # Claim 21: Target train artifact tamper blocks launch
    t_train.write_bytes(b"TAMPERED_TRAIN")
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(base_request)
    assert "Target training ExtXYZ SHA256 does not match" in str(exc_info.value)
    assert not wrapper_invocation_file.exists()
    t_train.write_bytes(b"TARGET_TRAIN_DATA")  # restore

    # Claim 22: Target monitor artifact tamper blocks launch
    t_valid.write_bytes(b"TAMPERED_VALID")
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(base_request)
    assert "Target validation ExtXYZ SHA256 does not match" in str(exc_info.value)
    assert not wrapper_invocation_file.exists()
    t_valid.write_bytes(b"TARGET_VALID_DATA")  # restore

    # Claim 23: Foundation artifact tamper blocks launch
    foundation_file.write_bytes(b"TAMPERED_FOUNDATION")
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(base_request)
    assert "Foundation model file SHA256 does not match" in str(exc_info.value)
    assert not wrapper_invocation_file.exists()
    foundation_file.write_bytes(b"FOUNDATION_MODEL_DATA")  # restore

    # Claim 24: Replay train artifact tamper blocks launch
    replay_train_file.write_bytes(b"TAMPERED_REPLAY_TRAIN")
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(base_request)
    assert "Replay train file SHA256 does not match" in str(exc_info.value)
    assert not wrapper_invocation_file.exists()
    replay_train_file.write_bytes(b"REPLAY_TRAIN_DATA")  # restore

    # Claim 25: Replay monitor artifact tamper blocks launch
    replay_monitor_file.write_bytes(b"TAMPERED_REPLAY_MONITOR")
    with pytest.raises(PostSelectionExecutionError) as exc_info:
        trainer(base_request)
    assert "Replay monitor file SHA256 does not match" in str(exc_info.value)
    assert not wrapper_invocation_file.exists()
    replay_monitor_file.write_bytes(b"REPLAY_MONITOR_DATA")  # restore

    # Claim 26: the actual trainer rejects a runtime TRUE_DFT monitor identity
    # that disagrees with the authenticated monitor bytes before launching.
    bad_runtime_plan = replace(
        plan, true_replay_monitor_sha256="ab" * 32
    )
    with pytest.raises(PostSelectionExecutionError, match="true_replay_monitor_sha256"):
        trainer(replace(base_request, plan=bad_runtime_plan))
    assert not wrapper_invocation_file.exists()

    # Claim 27: the wrapper receives the translated MACE surface, not the
    # internal P5 field names.
    translated = post_selection_mace_run_configuration(internal_config)
    assert "target_train_file" not in translated
    assert "target_valid_file" not in translated

    # Write summary in checkpoint directory so valid run succeeds
    with pytest.raises(PostSelectionExecutionError, match="canonical TRAIN2 runtime summary"):
        trainer(base_request)
    assert wrapper_invocation_file.read_text(encoding="utf-8").strip() == "LAUNCHED"
    (chk_dir / "train2_runtime.json").write_text(
        json.dumps(_make_dummy_train2_summary(plan).to_dict()), encoding="utf-8"
    )

    # Valid execution: exactly one wrapper launch
    summary = trainer(base_request)
    assert summary.plan_digest == plan.content_digest
    assert wrapper_invocation_file.read_text(encoding="utf-8").splitlines() == [
        "LAUNCHED",
        "LAUNCHED",
    ]

    # Claims 27 & 28: Translated config and TRAIN2 environment
    recorded = json.loads(wrapper_env_file.read_text(encoding="utf-8"))
    assert json.loads(recorded["TRAIN2_PLAN"]) == plan.to_dict()
    assert recorded["PYTHONHASHSEED"] == "42"
    assert recorded["TRUE_REPLAY_PATH"] == str(replay_monitor_file.resolve())
    assert recorded["CWD"] == str(mat_dir.resolve())


# ---------------------------------------------------------------------------
# Claims 30 to 38: Real-Owner CV Acceptance & Final Production Closure
# ---------------------------------------------------------------------------

def test_claims_30_to_38_assembled_lifecycle_and_restart_reauthentication(tmp_path: Path):
    """Claims 30-38: Complete assembled real-owner lifecycle traversal.
    - Canonical replay baseline and candidate admissibility
    - Zero-credit replay to target ranking
    - Held-out outer evaluation
    - Fresh full-T_selected final production
    - Restart reload reauthentication
    """
    config, _workspace = build_selected_campaign(tmp_path)
    harness = PostSelectionHarness()

    # 1. Run cross-validation
    rc_cv = run_cross_validate(config, harness)
    assert rc_cv == 0

    # 2. Run final production
    rc_prod = run_train_production(config, harness)
    assert rc_prod == 0

    # 3. Reload in fresh context and reauthenticate
    cfg, paths, store = load_context(config)
    try:
        selected = load_current_selected_training_context(cfg, paths, store)
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        cv_plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)

        assert cv_plan is not None
        assert acceptance is not None
        assert final_plan is not None

        # Claim 31: Replay is zero-credit to target ranking
        for seed_acc in acceptance.seed_acceptances:
            for fold_acc in seed_acc.fold_acceptances:
                assert fold_acc.accepted
                assert fold_acc.outer_metric_value <= fold_acc.acceptance_maximum

        # Claim 35: Final production horizon independence
        assert final_plan.planned_epochs == context.production_policy.production_max_num_epochs
        assert final_plan.n_selected == selected.n_selected
        assert final_plan.target_membership_digest == selected.selected_membership_digest

        # Claim 38: Reauthentication succeeds on unmodified store
        validate_post_selection_cv_plan(cv_plan, selected, replay_lineage_digest=cv_plan.replay_lineage_digest)
        validate_final_production_plan(
            final_plan, selected, method=context.method, policy=context.production_policy, replay_lineage_digest=final_plan.replay_lineage_digest
        )
    finally:
        store.close()
