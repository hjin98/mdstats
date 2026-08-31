"""P6 acceptance: the retired target-size architecture is structurally absent.

Three claims are kept separate here, because none of them may stand in for
another (P6 revision-4 section 5):

* the retired pre-V7 generation is rejected before any campaign record is read;
* a final-P6-created current workspace closes, reopens, and restarts unchanged;
* the retired V5/V6 target-size derived state is rejected before reuse.

The preserved P5A6 workspace claim lives in
``test_mlff_target_size_p6_p5a6_compatibility``.
"""

from __future__ import annotations

import argparse
import ast
import json
import tomllib
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_post_selection import (
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_final_production_plan,
)
from mdstats.training_data.campaign_target_size_cutover import (
    QUARANTINE_KEY_PREFIX,
    RETIRED_TARGET_SIZE_RECORD_KEYS,
    TargetSizeCutoverError,
    require_current_target_size_runtime,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    TargetSizeRegime,
    load_target_size_campaign_revision,
)

from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    run_cross_validate,
    run_train_production,
)
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

_PACKAGE = Path(mdstats.__file__).resolve().parent
_REPO = _PACKAGE.parent

#: Modules deleted by the P6 destructive cutover.  Structural absence, not a
#: runtime guard, is the evidence that no wrapper keeps them reachable.
RETIRED_MODULE_NAMES = (
    "target_size_study",
    "target_data_roles",
    "size_fidelity",
    "production_materialization",
    "work_queue",
    "multi_fidelity_evaluation",
    "lightweight_rank",
    "campaign_execution",
    "data7_bundle",
    "data7_archive",
    "adaptive_full_evaluation",
    "adaptive_migration",
    "adaptive_verification",
    "mlcv_aggregate",
    "mlcv_final",
    "mlcv_migration",
    "mlcv_select",
    "mlcv_verification",
    "target_coverage",
    "target_coverage_store",
    "target_coverage_feasibility",
    "target_coverage_exact_neighborhood",
    "target_coverage_exact_neighborhood_store",
    "target_coverage_sparse_index",
    "target_coverage_sparse_index_store",
    "target_coverage_sparse_forward_view",
    "target_multi_view_selector",
    "target_multi_view_selector_v2",
    "target_multi_view_selector_v2_resume",
    "target_multi_view_selection_state",
    "target_multi_view_selection_state_store",
    "target_multi_view_selection_state_v2",
    "target_multi_view_selection_history_v2",
    "target_multi_view_repair",
    "target_multi_view_repair_v2",
    "target_multi_view_qualification_v2",
    "mvsel2_hardening_runtime",
    "mvsel2_native_backend",
    "mvsel2_native_preflight",
    "mvsel2_phase_a_kernel",
    "mvsel2_phase_b_kernel",
    "mvsel2_repair_checkpoint_runtime",
    "mvsel2_selection_engine",
    "mvsel2_streaming_frontier",
    "mvsel2_v5_runtime",
    "mvidx1_forward_receipt_runtime",
    "mvqual_p2_runtime",
    "_sparse_vector_kernels",
    "_target_coverage_neighborhood",
    "_target_multi_view_scoring",
)

#: Public symbols that named retired target-size authority.
RETIRED_PUBLIC_SYMBOLS = (
    "TargetDataRoleFreeze",
    "TargetDataDomainRoleFreeze",
    "TargetSizeStudyPlan",
    "TargetSizeStudyPolicy",
    "TargetSizeStudyCandidate",
    "FIXED_TARGET_SIZES",
    "FIXED_TARGET_SIZE_CEILING",
    "TargetCoverageReference",
    "TargetCoverageSparseIndex",
    "TargetMultiViewSelectionPlanV2",
    "TargetMultiViewRepairPlanV2",
    "TargetMultiViewQualificationPlanV2",
    "TargetMultiViewSelectionStateCache",
    "Eval2TargetRole",
    "build_target_size_study",
    "build_target_data_role_freeze",
    "build_eval2_size_study_target_role",
    "build_eval2_coarse_size_study_target_role",
    "build_eval2_cv_target_role",
    "validate_target_size_study_authority",
    "materialize_candidate_prefix",
    "materialize_selected_prefix",
    "ProductionMaterializationRecord",
    "ProductionMaterializationPlan",
    "MlcvFinalSelectionRecord",
    "MlcvRoleCatalog",
    "build_mlcv_role_catalog",
    "build_data8_preparation_bundle",
    "TrainingCampaignPlan",
    "AdaptiveMigrationRecord",
)


# --- structural absence ----------------------------------------------------


def test_p6_retired_modules_are_deleted_not_wrapped():
    present = [
        name
        for name in RETIRED_MODULE_NAMES
        if (_PACKAGE / "training_data" / f"{name}.py").exists()
    ]
    assert not present, present
    assert not (_PACKAGE / "_mvsel2_native.c").exists()


def test_p6_retired_public_symbols_are_unexported():
    offenders = [
        name
        for name in RETIRED_PUBLIC_SYMBOLS
        if hasattr(mdstats, name)
        or hasattr(mdstats.training_data, name)
        or name in mdstats.__all__
        or name in mdstats.training_data.__all__
    ]
    assert not offenders, offenders


def test_p6_no_source_file_references_a_retired_target_size_authority():
    """No surviving production module imports or names a retired owner."""

    needles = (
        "TargetDataRoleFreeze",
        "target_size_study",
        "target_multi_view",
        "target_coverage",
        "mvsel2_",
        "mvqual_p2",
        "mvidx1_forward",
        "FIXED_TARGET_SIZES",
        "domain_prefix_digests",
        "size_development_complement",
        "prescribed_target_size_evaluation_frames",
    )
    offenders: list[str] = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        if path.name in {"campaign_target_size_cutover.py", "campaign_cli.py"}:
            # The reject-only obsolete-generation detector must name the retired
            # record keys in order to recognise and quarantine them.  It reads
            # names only and never decodes a retired payload, which
            # `test_p6_quarantined_retired_state_is_never_semantically_decoded`
            # asserts structurally.  The CLI facade docstring records, in prose,
            # which retired runtimes it no longer installs.
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                offenders.append(f"{path.relative_to(_PACKAGE)}: {needle}")
    assert not offenders, offenders


def test_p6_public_command_surface_is_the_current_lifecycle_only():
    parser = cli.build_parser()
    sub = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    assert sorted(sub.choices) == [
        "advance",
        "cross-validate",
        "doctor",
        "guide",
        "init",
        "prepare",
        "select-target-size",
        "status",
        "storage",
        "train-production",
    ]


def test_p6_public_campaign_exports_are_current_and_facade_is_exact():
    expected = {
        "MLFF_DATA9B3_VERSION",
        "CAMPAIGN_CLI_SCHEMA",
        "CURRENT_PREPARE_RESTART_RECEIPT_SCHEMA",
        "CURRENT_PREPARE_CONTRACT_VERSION",
        "CampaignCliError",
        "CampaignPaths",
        "CampaignStore",
        "StageState",
        "build_parser",
        "main",
    }
    assert set(cli.__all__) == expected

    import mdstats.training_data as training_data
    import mdstats.training_data.campaign_cli as campaign_cli

    assert set(campaign_cli.__all__) == expected
    assert "PREPARE_RESTART_RECEIPT_SCHEMA" not in dir(cli)
    assert "PREPARE_CONTRACT_VERSION" not in dir(cli)
    assert "PREPARE_RESTART_RECEIPT_SCHEMA" not in dir(campaign_cli)
    assert "PREPARE_CONTRACT_VERSION" not in dir(campaign_cli)
    assert all(not name.startswith("PREPARE_") for name in training_data.__all__)


def test_p6_generated_config_and_example_expose_only_current_authority():
    generated = tomllib.loads(
        cli._config_template(
            workspace="/tmp/p6-test",
            training_root="/tmp/p6-training",
            foundation_model="/tmp/p6-foundation",
            replay_set="/tmp/p6-replay",
        )
    )
    example = tomllib.loads(
        (_REPO / "campaign.toml.example").read_text(encoding="utf-8")
    )
    for cfg in (generated, example):
        size = cfg["target_data"]["size_convergence"]
        assert {
            "target_size_power_min",
            "target_size_power_max",
            "evaluation_size_powers",
            "fidelity_epochs",
        } <= set(size)
        assert "preflight" not in cfg
        for method_name in ("naive_fine_tuning", "multihead_replay"):
            method = cfg["training"][method_name]
            assert "cross_validation_folds" not in method
            assert "fold_partition_seed" not in method
            assert "seed_mode" not in method
        cv = cfg["post_selection"]["cv"]
        assert {"fold_count", "partition_seed", "seeds"} <= set(cv)
        assert "foundation_audit_temporary_ram_mib" not in cfg.get("performance", {})
        assert "parallel_dynamics_jobs" not in cfg.get("execution", {})
        assert "remove_frame_cache_after_prepare" not in cfg.get("cleanup", {})
        assert "remove_evaluation_graph_cache_after_evaluate" not in cfg.get("cleanup", {})


def test_p6_preparation_projection_excludes_cv_authoring():
    cfg = {
        "partition": {
            "minimum_block_frames": 32,
            "purge_units_between_roles": 1,
            "cross_validation_folds": 5,
            "cross_validation_seed": 42,
        },
        "random": {
            "feature_projection_seed": 101,
            "online_monitor_seed": 202,
            "fold_partition_seed": 303,
        },
        "training": {
            "policy_generation": "train2",
            "multihead_replay": {
                "enabled": True,
                "seeds": [1, 2],
                "cross_validation_folds": 5,
                "fold_partition_seed": 303,
                "seed_mode": "optimizer_only",
            },
        },
    }
    proj = cli._preparation_config_projection(cfg)
    assert "cross_validation_folds" not in proj["partition"]
    assert "cross_validation_seed" not in proj["partition"]
    assert "fold_partition_seed" not in proj["random"]
    assert "cross_validation_folds" not in proj["training"]["multihead_replay"]
    assert "fold_partition_seed" not in proj["training"]["multihead_replay"]
    assert "seed_mode" not in proj["training"]["multihead_replay"]


def test_p6_target_size_ladder_has_no_fixed_16384_ceiling():
    config = {
        "target_data": {
            "size_convergence": {
                "target_size_power_min": 7,
                "target_size_power_max": 15,
                "evaluation_size_powers": [8, 9, 10],
                "fidelity_epochs": [1, 3, 10],
            }
        },
        "training": {
            "multihead_replay": {"enabled": True, "seeds": [1, 2]},
            "naive_fine_tuning": {"enabled": False},
        },
    }
    resolved = mdstats.resolve_target_size_policy_from_config(config)
    assert resolved.nmax == 2**15


def test_p6_current_guide_and_help_have_one_public_lifecycle():
    guide = " ".join(cli.GUIDE_TEXT.split())
    lifecycle = (
        "init -> doctor -> prepare -> select-target-size -> "
        "cross-validate -> train-production"
    )
    assert lifecycle in guide
    assert "the orthogonal storage command" in guide.lower()
    assert "pre-target fold controls are not generated" in guide.lower()
    assert "downstream accelerator and long-production qualification" in guide.lower()

    parser = cli.build_parser()
    help_text = parser.format_help()
    assert lifecycle in help_text
    assert "preflight" not in help_text.lower()
    assert "target-size-v5" not in help_text.lower()


def test_p6_current_contract_and_source_map_do_not_advertise_retired_authority():
    """Current source/docs expose no V5/V6 authority as a live contract."""

    current_sources = (
        _PACKAGE / "training_data" / "_campaign_cli_core.py",
        _PACKAGE / "training_data" / "campaign_cli.py",
        _PACKAGE / "training_data" / "campaign_target_size_runtime.py",
        _PACKAGE / "training_data" / "campaign_post_selection.py",
        _PACKAGE / "training_data" / "campaign_post_selection_runtime.py",
    )
    current_documents = (
        _REPO / "campaign.toml.example",
        _REPO / "docs" / "guides" / "mlff_campaign_cli_user_guide.md",
        _REPO / "docs" / "specs" / "training_data" / "mlff_data9b3_campaign_cli_spec.md",
        _REPO / "docs" / "specs" / "training_data" / "mlff_data_stage_plan_spec.md",
        _REPO / "docs" / "arch_manuals" / "mlff_training_data_architecture.md",
        _REPO / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json",
        *sorted((_REPO / "docs" / "arch_manuals" / "mlff_training_data").glob("*.md")),
    )
    forbidden = (
        "target-size-v5",
        "TARGET-SIZE-V5",
        "target_size_study_digest",
        "target_data_role_freeze_digest",
    )
    offenders = [
        f"{path.relative_to(_REPO)}: {needle}"
        for path in (*current_sources, *current_documents)
        for needle in forbidden
        if needle in path.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders


def test_p6_authenticated_compatibility_driver_is_mandatory_and_pinned():
    """The P5A6 proof must authenticate its producer instead of skipping."""

    driver = (
        _REPO / "qualification" / "p6-p5a6-compat" / "qualify_p5a6_to_p6.py"
    ).read_text(encoding="utf-8")
    assert 'BASELINE_COMMIT = "1670275487d29bbcde4c59efafdef9d1f8b0ced7"' in driver
    assert 'BASELINE_TREE = "17e2c5609974712bda1efd3375f09f42da830f68"' in driver
    assert '"git", "worktree", "add", "--detach"' in driver
    assert '"rev-parse", "HEAD^{tree}"' in driver
    assert "_assert_import_roots" in driver
    assert "pytest.mark.skip" not in driver
    assert "pytest.skip" not in driver
    assert "pytest.mark.skipif" not in driver


def test_p6_prepare_help_keeps_preparation_outside_selection():
    parser = cli.build_parser()
    sub = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    prepare_help = next(
        action.help.lower()
        for action in sub._choices_actions
        if action.dest == "prepare"
    )
    assert "does not select a target size" in prepare_help
    assert "per-domain" not in prepare_help
    assert "data7" not in prepare_help
    assert "preflight" not in prepare_help


# --- retired configuration generation: reject before any record is read ----


@pytest.mark.parametrize(
    "generation", ["adaptive_stop_v3", "adaptive", "adaptive_stop", "legacy"]
)
def test_p6_retired_policy_generation_is_rejected_with_reset_guidance(
    tmp_path: Path, generation: str
):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    text = config.read_text(encoding="utf-8").replace(
        'policy_generation = "train2"', f'policy_generation = "{generation}"'
    )
    config.write_text(text, encoding="utf-8")
    with pytest.raises(cli.CampaignCliError) as excinfo:
        p4d._run(config, "prepare")
    message = str(excinfo.value)
    assert "retired" in message
    assert "train2" in message
    assert "prepare" in message


def test_p6_missing_policy_generation_is_rejected(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    text = config.read_text(encoding="utf-8").replace(
        'policy_generation = "train2"\n', ""
    )
    config.write_text(text, encoding="utf-8")
    with pytest.raises(cli.CampaignCliError) as excinfo:
        p4d._run(config, "prepare")
    assert "policy_generation" in str(excinfo.value)


# --- retired derived state: rejected before reuse ---------------------------


def test_p6_retired_target_size_workspace_is_rejected_before_reuse(tmp_path: Path):
    """A workspace holding retired derived target-size records refuses to run.

    The rejection comes from the real currentness owner and happens before any
    retired payload is deserialized: the record is written as an opaque mapping
    that no current loader could decode into V7 authority.
    """

    config, workspace = p4d._fixture_campaign(tmp_path)
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        for key in ("target_size_study", "target_data_role_freeze"):
            store.put_record(
                key,
                {
                    "schema": "mdstats.target-size-study-plan.v11",
                    "selected_target_size": 8192,
                    "qualified_sizes": [128, 256, 512],
                },
            )
        with pytest.raises(TargetSizeCutoverError) as excinfo:
            require_current_target_size_runtime(store)
    finally:
        store.close()
    message = str(excinfo.value)
    assert "retired target-size" in message
    assert "prepare" in message
    assert "never migrated" in message or "not migrated" in message

    # `prepare` performs the destructive cutover: the retired records are
    # quarantined under a namespace no current loader reads, never translated.
    assert cli.main(["--config", str(config), "prepare"]) == 0
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = require_current_target_size_runtime(store)
        assert revision.state.regime is TargetSizeRegime.CURRENT
        live = set(store.record_keys())
        assert not (live & set(RETIRED_TARGET_SIZE_RECORD_KEYS))
        quarantined = [k for k in live if k.startswith(QUARANTINE_KEY_PREFIX)]
        assert any(k.endswith("target_size_study") for k in quarantined)
        # The retired selected size never becomes current authority.
        assert revision.state.terminal is None
    finally:
        store.close()


def test_p6_quarantined_retired_state_is_never_semantically_decoded():
    """The cutover reads record *names*; it never decodes a retired payload."""

    source = (
        _PACKAGE / "training_data" / "campaign_target_size_cutover.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    inventory = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "inventory_retired_target_size_state"
    )
    called = {
        node.func.attr
        for node in ast.walk(inventory)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "get_record" not in called
    assert "get_payload" not in called
    assert "record_keys" in called


# --- P6 -> P6 restart -------------------------------------------------------


def test_p6_current_workspace_closes_reopens_and_restarts_deterministically(
    tmp_path: Path,
):
    """A workspace created by the final P6 candidate survives close/reopen."""

    config, workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config, PostSelectionHarness()) == 0
    assert run_train_production(config, PostSelectionHarness()) == 0

    def snapshot() -> dict[str, object]:
        cfg, paths = cli._load_config(config)
        store = CampaignStore(paths.state_db)
        try:
            revision = require_current_target_size_runtime(store)
            selected = load_current_selected_training_context(cfg, paths, store)
            context = build_post_selection_context(cfg, paths, store, trainer=None)
            acceptance = resolve_current_cv_acceptance(context)
            final_plan = resolve_current_final_production_plan(context)
            assert revision.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
            assert acceptance is not None and acceptance.accepted
            assert final_plan is not None
            return {
                "state": revision.state.content_digest,
                "generation": revision.state.generation,
                "n_selected": selected.n_selected,
                "membership": list(selected.selected_membership),
                "binding": selected.binding.content_digest,
                "method": context.method.content_digest,
                "acceptance": acceptance.content_digest,
                "final": final_plan.content_digest,
            }
        finally:
            store.close()

    first = snapshot()
    second = snapshot()
    assert first == second

    # Rerunning the owning commands on the reopened workspace is a no-op that
    # reauthenticates rather than rebuilding.
    assert run_cross_validate(config, PostSelectionHarness()) == 0
    assert run_train_production(config, PostSelectionHarness()) == 0
    assert snapshot() == first

    # `status` projects the complete current lifecycle from those same owners.
    assert cli.main(["--config", str(config), "status"]) == 0


def test_p6_r8_data5_fresh_construction_and_serialization_neutrality():
    """Fresh DATA5 serialization omits CV fold plans; legacy v1 loads compatibly."""
    from mdstats.training_data.data5_bundle import (
        DATA5_PARTITION_BUNDLE_SCHEMA,
        LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA,
        Data5PartitionBundle,
    )
    from mdstats.training_data.role_budget import (
        PARTITION_ROLE_BUDGET_POLICY_SCHEMA,
        PartitionRoleBudgetPolicy,
    )
    from mdstats.training_data.partition import (
        PARTITION_POLICY_SCHEMA,
        PartitionPolicy,
    )

    budget = PartitionRoleBudgetPolicy()
    assert budget.schema == PARTITION_ROLE_BUDGET_POLICY_SCHEMA
    budget_dict = budget.to_dict()
    assert "cross_validation_folds" not in budget_dict
    assert "checkpoint_monitor_minimum_units_per_fold" not in budget_dict

    policy = PartitionPolicy(role_budget=budget)
    assert policy.schema == PARTITION_POLICY_SCHEMA
    policy_dict = policy.to_dict()
    assert "cross_validation_seed" not in policy_dict


def test_p6_r8_transitional_storage_fails_closed_on_consequential_tiers(tmp_path: Path):
    """Consequential storage tiers fail closed to CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1."""
    from mdstats.training_data._campaign_cli_core import (
        CampaignCliError,
        command_archive,
        command_cleanup,
        command_deduplicate,
    )

    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config, PostSelectionHarness()) == 0
    assert run_train_production(config, PostSelectionHarness()) == 0

    for tier in ("recompute", "compact", "archive"):
        args = argparse.Namespace(config=str(config), tier=tier, dry_run=False, apply=False, keep_preparation_caches=False)
        with pytest.raises(CampaignCliError, match="CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1"):
            command_cleanup(args)
        # Parser rejects consequential tiers
        with pytest.raises(SystemExit):
            cli.main(["--config", str(config), "storage", "cleanup", "--tier", tier])

    args_dedup = argparse.Namespace(config=str(config), apply=True)
    with pytest.raises(CampaignCliError, match="CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1"):
        command_deduplicate(args_dedup)
    with pytest.raises(SystemExit):
        cli.main(["--config", str(config), "storage", "deduplicate", "--apply"])

    args_archive = argparse.Namespace(config=str(config), archive_action="create")
    with pytest.raises(CampaignCliError, match="CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1"):
        command_archive(args_archive)
    with pytest.raises(SystemExit):
        cli.main(["--config", str(config), "storage", "archive", "create"])

    # Safe and cache tiers remain operational
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "safe"]) == 0
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "cache"]) == 0
    assert cli.main(["--config", str(config), "storage", "report"]) == 0


def test_p6_r8_final_production_completion_distinct_digest_and_verification(tmp_path: Path):
    """FinalProductionCompletion binds evidence digests and differs from plan digest."""
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_context,
        resolve_current_final_production_completion,
        resolve_current_final_production_plan,
    )

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=None)
        # Before training production, completion is None
        assert resolve_current_final_production_completion(context) is None
    finally:
        store.close()

    assert run_cross_validate(config, PostSelectionHarness()) == 0
    assert run_train_production(config, PostSelectionHarness()) == 0

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        context = build_post_selection_context(cfg, paths, store, trainer=None)
        plan = resolve_current_final_production_plan(context)
        completion = resolve_current_final_production_completion(context)
        assert plan is not None
        assert completion is not None
        # Must NOT alias plan digest
        assert completion.content_digest != plan.content_digest
        assert len(completion.runs) == len(plan.required_final_seeds)
    finally:
        store.close()


def test_p6_r9_storage_structural_cleanup_authorization():
    """Structural invariant: cleanup has only safe/cache, no retired stage/path hooks."""
    import inspect
    from mdstats.training_data import _campaign_cli_core as cli_core

    assert cli_core._MANUAL_RECLAMATION_TIERS == ("safe", "cache")

    parser = cli_core.build_parser()
    storage_sub = next(
        action for action in parser._actions
        if getattr(action, "dest", None) == "command"
    ).choices["storage"]

    cleanup_parser = next(
        action for action in storage_sub._actions
        if getattr(action, "dest", None) == "storage_command"
    ).choices["cleanup"]

    tier_action = next(
        action for action in cleanup_parser._actions
        if "--tier" in getattr(action, "option_strings", [])
    )
    assert set(tier_action.choices) == {"safe", "cache"}
    assert "recompute" not in tier_action.choices
    assert "compact" not in tier_action.choices
    assert "archive" not in tier_action.choices

    # Inspect cleanup implementation source
    cleanup_src = inspect.getsource(cli_core._campaign_cleanup)
    assert 'evaluate' not in cleanup_src or '_effective_stage' not in cleanup_src
    assert 'verify' not in cleanup_src or '_effective_stage' not in cleanup_src
    assert 'data7' not in cleanup_src
    assert 'data8' not in cleanup_src
    assert 'preflight' not in cleanup_src


def test_p6_r9_storage_functional_retention_and_historical_path_trap(tmp_path: Path):
    """Historical path trap: unowned retired paths are retained, not deleted by pathname."""
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)

    # Place unowned directories with retired historical names inside workspace
    hist_dirs = [
        paths.internal / "data7-cache",
        paths.internal / "data8-fixed-cache",
        paths.internal / "evaluation-graphs",
    ]
    for d in hist_dirs:
        d.mkdir(parents=True, exist_ok=True)
        (d / "payload.bin").write_bytes(b"historical-content")

    # Place a genuinely current reconstructible cache
    frame_cache = paths.internal / "frame-cache"
    frame_cache.mkdir(parents=True, exist_ok=True)
    (frame_cache / "cache.mmap").write_bytes(b"reconstructible")

    # Safe cleanup: preserves historical paths and frame cache
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "safe"]) == 0
    for d in hist_dirs:
        assert (d / "payload.bin").is_file(), f"{d} must be retained"
    assert (frame_cache / "cache.mmap").is_file()

    # Cache cleanup: preserves uncertified historical paths, removes genuinely current frame-cache
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "cache"]) == 0
    for d in hist_dirs:
        assert (d / "payload.bin").is_file(), f"{d} must not be deleted by pathname alone"
    assert not frame_cache.exists(), "current frame-cache must be removed by cache tier"

