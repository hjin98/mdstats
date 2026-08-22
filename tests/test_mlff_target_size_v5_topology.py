from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import mdstats
import pytest
from mdstats.training_data import campaign_cli
from mdstats.training_data import _campaign_cli_core as campaign_core
from mdstats.training_data import production_materialization
from mdstats.training_data.target_size_study import FIXED_TARGET_SIZES


_RETIRED_ENSURE_NAMES = (
    "_ensure_size_halve2_plan",
    "_ensure_size_fidelity2_execution_plan",
    "_ensure_target_multi_view_migration",
    "_resolve_active_target_data_ladder",
    "_ensure_target_production_corpus_decision",
    "_load_verified_target_size_convergence_authority",
)


def test_v5_fixed_universe_and_public_authority_are_unique() -> None:
    assert FIXED_TARGET_SIZES == (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    assert mdstats.TargetSizeStudyPolicy().candidate_sizes == FIXED_TARGET_SIZES
    assert mdstats.TargetMultiViewQualificationPolicyV2().candidate_sizes == FIXED_TARGET_SIZES
    for retired in (
        "TargetDataLadderPlan",
        "TargetSizeConvergencePlan",
        "SizeHalve2Plan",
        "SizeFidelity2ExecutionPlan",
        "TargetMultiViewMigrationPlan",
        "TargetProductionCorpusDecision",
        "TargetMultiViewSelectorPolicy",
        "TargetMultiViewSelectionPlan",
        "build_target_multi_view_selection_plan",
        "TargetMultiViewRepairPolicy",
        "TargetMultiViewRepairPlan",
        "build_target_multi_view_repair_plan",
    ):
        assert not hasattr(mdstats, retired), retired


def test_prepare_runtime_is_direct_repair2_mvqual2_target_size_study() -> None:
    source = inspect.getsource(campaign_cli._prepare_materialization)
    ordered = (
        "_ensure_target_multi_view_selection_v2(",
        "_ensure_target_multi_view_repair_v2(",
        "_ensure_target_multi_view_qualification_v2(",
        "_ensure_target_size_study(",
    )
    positions = [source.index(token) for token in ordered]
    assert positions == sorted(positions)
    for retired in _RETIRED_ENSURE_NAMES:
        assert retired not in source
        assert not hasattr(campaign_cli, retired)
    assert "No rescue sizes are permitted" in source
    assert "rescue above 16384 is forbidden" in source


def test_prepare_receipt_hard_cuts_retired_derived_authorities() -> None:
    keys = set(campaign_cli._PREPARE_RECEIPT_RECORD_KEYS)
    assert {
        "target_coverage_feasibility",
        "target_coverage_sparse_index",
        "target_multi_view_selection_v2",
        "target_multi_view_repair_v2",
        "target_multi_view_qualification_v2",
        "target_size_study",
    } <= keys
    assert not keys.intersection(
        {
            "target_data_ladder",
            "target_size_convergence",
            "target_multi_view_migration",
            "size_halve2",
            "size_fidelity2",
            "target_production_corpus_decision",
        }
    )


def test_target_size_funnel_finishes_before_held_out_cv() -> None:
    eval_source = inspect.getsource(campaign_cli._command_evaluate_train2)
    role_source = inspect.getsource(campaign_cli._eval2_target_role_for_run)
    assert "attach_epoch_3_evidence" in eval_source
    assert "attach_epoch_10_evidence" in eval_source
    assert "attach_epoch_30_evidence" in eval_source
    assert "target-size selection frozen" in eval_source
    assert 'for stage_name in ("prepare", "preflight", "train", "evaluate")' in eval_source
    assert "Held-out CV EVAL2 is blocked until selected_target_size is frozen" in role_source
    for retired_mutator in ("with_stage_b0_evidence", "with_stage_b_evidence", "with_stage_c_evidence"):
        assert retired_mutator not in eval_source
        assert retired_mutator not in role_source


def test_held_out_cv_runtime_is_rejected_before_target_size_freeze(monkeypatch) -> None:
    monkeypatch.setattr(campaign_core, "_eval2_label_domain_id", lambda *_args, **_kwargs: "d0")
    run = SimpleNamespace(
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=0,
    )
    study = SimpleNamespace(outcome=mdstats.OUTCOME_AWAITING_EPOCH_3)
    with pytest.raises(campaign_core.CampaignCliError, match="blocked until selected_target_size is frozen"):
        campaign_core._eval2_target_role_for_run(
            store=object(),
            target_size_study=study,
            repair2=object(),
            role_freeze=object(),
            bundle=object(),
            run=run,
        )


def test_screening_materialization_uses_exact_stage_sizes_and_ordered_seed_set(monkeypatch) -> None:
    method = SimpleNamespace(mode="multihead", fold_partition_seed=17)
    monkeypatch.setattr(campaign_core, "_training_method_specs", lambda _cfg: (method,))
    study = SimpleNamespace(
        outcome=mdstats.OUTCOME_AWAITING_EPOCH_10,
        next_training_sizes=(512, 2048),
        policy=SimpleNamespace(screening_optimizer_seeds=(7, 11)),
    )
    variants = campaign_core._target_size_materialization_variants({}, study=study)
    assert [(item.selection_size, item.seed) for item in variants] == [
        (512, 7),
        (512, 11),
        (2048, 7),
        (2048, 11),
    ]
    assert all(item.cross_validation_folds == 0 for item in variants)


def test_post_selection_verification_cannot_advance_target_size() -> None:
    functions = (
        campaign_cli._command_verify_train2_deploy,
        campaign_cli._command_verify_train2_pes,
        campaign_cli._command_verify_train2_relax,
        campaign_cli._command_verify_train2_dyn,
        campaign_cli._finalize_train2_dyn,
    )
    source = "\n".join(inspect.getsource(fn) for fn in functions)
    assert "_load_verified_target_size_study_authority" in source
    assert "attach_epoch_" not in source
    assert "with_stage_" not in source
    assert "target_production_corpus" not in source


def test_candidate_and_selected_prefix_materializations_are_distinct_contracts() -> None:
    source = inspect.getsource(production_materialization.ProductionMaterializationPlan.__post_init__)
    assert '"target_size_candidate"' in source
    assert '"selected_production_prefix"' in source
    assert "Only target_size_candidate materializations may bind the pre-selection development evaluation cohort" in source
    data7_source = inspect.getsource(__import__(
        "mdstats.training_data.data7_bundle", fromlist=["build_data7_preparation_bundle"]
    ).build_data7_preparation_bundle)
    assert "prescribed_selection_frame_uids" in data7_source
    assert "no second ranking is performed" in data7_source


def test_generated_config_exposes_no_retired_target_size_rescue_controls() -> None:
    template = campaign_cli._config_template(
        workspace="workspace",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay_train.xyz",
        replay_monitor="replay_monitor.xyz",
        acceleration_backend="e3nn",
    )
    for retired in (
        "coverage_rescue_activated",
        "coverage_rescue_candidate_sizes",
        "coverage_rescue_min_qualifiers",
        "size_halve2",
        "size_fidelity2",
        "mvmigrate1",
        "target_data_ladder",
    ):
        assert retired not in template.lower()


def test_prepare_contract_signature_is_v5_only_and_current_upstreams_are_reusable() -> None:
    signature = campaign_cli._prepare_contract_signature()
    assert signature["prepare_contract_version"] == "target-size-v5.2026-08.v1"
    assert {
        "target_data2c_mvidx1_version",
        "target_data2c_mvsel2_version",
        "target_data2c_repair2_version",
        "target_data2c_mvqual2_version",
        "target_size_study_version",
    } <= set(signature)
    for retired_key in (
        "target_data2c_mvsel1_version",
        "target_data2c_repair1_version",
        "target_data2c_mvqual1_version",
        "target_data2c_ladder_version",
        "target_data2c_mvmigrate1_version",
        "target_data2c_migrated_ladder_version",
        "target_data2d_migrated_convergence_version",
        "target_data2e_migrated_production_version",
    ):
        assert retired_key not in signature

    # Selective restart reuse is owned by each authenticated current upstream
    # authority rather than by a migration bridge. Runtime installers wrap some
    # helpers, so inspect the owning source file rather than mutated callables.
    core_source = Path(campaign_core.__file__).read_text(encoding="utf-8")
    for helper_name in (
        "_ensure_target_coverage_feasibility",
        "_ensure_target_coverage_sparse_index",
        "_ensure_target_multi_view_selection_v2",
        "_ensure_target_multi_view_repair_v2",
        "_ensure_target_multi_view_qualification_v2",
        "_ensure_target_size_study",
    ):
        start = core_source.index(f"def {helper_name}(")
        next_def = core_source.find("\ndef ", start + 1)
        helper_source = core_source[start:] if next_def < 0 else core_source[start:next_def]
        assert "get_record_optional" in helper_source
        assert "reused" in helper_source
    start = core_source.index("def _try_reuse_completed_prepare(")
    next_def = core_source.find("\ndef ", start + 1)
    reuse_source = core_source[start:] if next_def < 0 else core_source[start:next_def]
    assert 'if not store.has_record("prepare_restart_receipt"):' in reuse_source
    assert "return False" in reuse_source
    assert "0.20.68a0" not in reuse_source
