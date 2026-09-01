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
import os
import time
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
    """The P6 training lifecycle, plus the accepted P7 downstream family.

    P6's invariant is that the retired pre-V7 topology never returns and that
    the training lifecycle stays exactly as closed. Post-production
    qualification is a separate accepted downstream owner, not a training
    command: `advance` does not run it, and it appears in no lifecycle stage.
    """

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
        "qualification",
        "select-target-size",
        "status",
        "storage",
        "train-production",
    ]
    assert "qualification" not in {name for name, _description in cli.PIPELINE}


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


def test_p6_r8_retired_loss_tiers_are_not_current_product_authority(tmp_path: Path):
    """The retired `recompute`/`compact` tiers are rejected by name.

    The storage reset replaced the P6 quarantine with owner-driven archive and
    deduplication, but it did not resurrect the consequential-loss tiers:
    intentionally lossy history pruning still requires its own product decision.
    """

    config, _workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config, PostSelectionHarness()) == 0
    assert run_train_production(config, PostSelectionHarness()) == 0

    for tier in ("recompute", "compact"):
        with pytest.raises(SystemExit):
            cli.main(["--config", str(config), "storage", "cleanup", "--tier", tier])

    # Archive and deduplication are current, and both plan before they mutate.
    assert cli.main(["--config", str(config), "storage", "archive", "create", "--dry-run"]) == 0
    assert cli.main(["--config", str(config), "storage", "deduplicate", "--dry-run"]) == 0
    assert cli.main(["--config", str(config), "storage", "archive", "list"]) == 0
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "safe", "--apply"]) == 0
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "cache", "--apply"]) == 0
    assert cli.main(["--config", str(config), "storage", "report"]) == 0
    assert cli.main(["--config", str(config), "storage", "report", "--deep"]) == 0


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


def test_p6_r10_configuration_and_help_truthfulness():
    """R10-A: Generated config, example, and GUIDE_TEXT describe only safe|cache."""
    from mdstats.training_data import _campaign_cli_core as cli_core

    raw_config = cli_core._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay-train.xyz",
        replay_monitor="replay-monitor.xyz",
        replay_true_labels="true-labels",
    )
    assert "storage cleanup --tier safe|cache." in raw_config
    assert "safe|cache|recompute" not in raw_config
    assert "recompute|compact|archive" not in raw_config

    example_text = Path("campaign.toml.example").read_text(encoding="utf-8")
    assert "storage cleanup --tier safe|cache." in example_text
    assert "safe|cache|recompute" not in example_text
    assert "recompute|compact|archive" not in example_text

    guide = cli_core.GUIDE_TEXT
    assert "storage report                          owner-driven read-only inventory" in guide
    assert "storage cleanup --tier safe --dry-run   inspect zero-loss cleanup" in guide
    assert "storage cleanup --tier cache --dry-run  inspect owner-certified cache eviction" in guide
    assert "storage archive create --apply" in guide
    assert "storage deduplicate --dry-run|--apply" in guide
    assert "retired recompute and compact" in guide
    # The retired loss tiers are never offered as commands.
    assert "storage cleanup --tier recompute" not in guide
    assert "storage cleanup --tier compact" not in guide


def test_p6_r10_cli_namespace_and_legacy_cleanup_removal(tmp_path: Path):
    """R10-B: Top-level cleanup is rejected and _normalize_legacy_storage_argv is absent."""
    from mdstats.training_data import _campaign_cli_core as cli_core

    assert not hasattr(cli_core, "_normalize_legacy_storage_argv")
    parser = cli_core.build_parser()
    sub_action = next(a for a in parser._actions if getattr(a, "dest", None) == "command")
    assert "cleanup" not in sub_action.choices
    assert "archive" not in sub_action.choices
    assert "deduplicate" not in sub_action.choices

    storage_sub = sub_action.choices["storage"]
    storage_action = next(a for a in storage_sub._actions if getattr(a, "dest", None) == "storage_command")
    assert set(storage_action.choices) == {"report", "cleanup", "archive", "deduplicate"}

    cleanup_parser = storage_action.choices["cleanup"]
    tier_action = next(a for a in cleanup_parser._actions if "--tier" in getattr(a, "option_strings", []))
    assert set(tier_action.choices) == {"safe", "cache"}

    config, _workspace = build_selected_campaign(tmp_path)
    with pytest.raises(SystemExit):
        cli_core.main(["cleanup", "--tier", "safe"])

    assert cli_core.main(["--config", str(config), "storage", "cleanup", "--tier", "safe"]) == 0


def test_p6_r12_historical_run_tree_trap_across_marker_cases(tmp_path: Path):
    """R12 Section 4.1: Historical workspace/runs trap is retained across all active_process/PID states."""
    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)

    marker_cases = [
        ("no_marker", None),
        ("malformed_marker", "invalid-json-content{{{"),
        ("dead_pid", json.dumps({"pid": 999999999, "timestamp": "2026-08-31T00:00:00Z"})),
        ("live_pid", json.dumps({"pid": os.getpid(), "timestamp": "2026-08-31T00:00:00Z"})),
    ]

    for case_name, marker_content in marker_cases:
        run_dir = paths.runs / f"legacy-run-{case_name}"
        obsolete_dir = run_dir / "obsolete-runtime-old"
        (obsolete_dir / "logs").mkdir(parents=True, exist_ok=True)
        (obsolete_dir / "tmp").mkdir(parents=True, exist_ok=True)
        (obsolete_dir / "staging").mkdir(parents=True, exist_ok=True)
        (obsolete_dir / "scratch").mkdir(parents=True, exist_ok=True)
        (obsolete_dir / "checkpoint-model-cache").mkdir(parents=True, exist_ok=True)
        (obsolete_dir / "evaluation-graph-cache").mkdir(parents=True, exist_ok=True)
        (obsolete_dir / "prediction-cache").mkdir(parents=True, exist_ok=True)

        stdout_log = obsolete_dir / "logs" / "stdout.log"
        stdout_log.write_text("historical log output\n", encoding="utf-8")
        tmp_payload = obsolete_dir / "tmp" / "payload"
        tmp_payload.write_bytes(b"tmp-bytes")
        staging_payload = obsolete_dir / "staging" / "payload"
        staging_payload.write_bytes(b"staging-bytes")
        scratch_payload = obsolete_dir / "scratch" / "payload"
        scratch_payload.write_bytes(b"scratch-bytes")
        model_payload = obsolete_dir / "checkpoint-model-cache" / "model.pt"
        model_payload.write_bytes(b"model-pt-bytes")
        graph_payload = obsolete_dir / "evaluation-graph-cache" / "payload"
        graph_payload.write_bytes(b"graph-bytes")
        pred_payload = obsolete_dir / "prediction-cache" / "payload"
        pred_payload.write_bytes(b"pred-bytes")

        marker_file = run_dir / "active_process.json"
        if marker_content is not None:
            marker_file.write_text(marker_content, encoding="utf-8")

        # Set mtime older than stale_age_hours (e.g. 48 hours old)
        old_time = time.time() - 48.0 * 3600.0
        for p in [run_dir, obsolete_dir, stdout_log, tmp_payload, staging_payload, scratch_payload, model_payload, graph_payload, pred_payload]:
            os.utime(p, (old_time, old_time))
        if marker_content is not None:
            os.utime(marker_file, (old_time, old_time))

        # Invoke public safe and cache cleanup
        assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "safe"]) == 0
        assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "cache"]) == 0

        # Every byte under the trap must remain intact
        assert stdout_log.read_text(encoding="utf-8") == "historical log output\n"
        assert tmp_payload.read_bytes() == b"tmp-bytes"
        assert staging_payload.read_bytes() == b"staging-bytes"
        assert scratch_payload.read_bytes() == b"scratch-bytes"
        assert model_payload.read_bytes() == b"model-pt-bytes"
        assert graph_payload.read_bytes() == b"graph-bytes"
        assert pred_payload.read_bytes() == b"pred-bytes"

        # The marker itself must remain and NOT be unlinked
        if marker_content is not None:
            assert marker_file.is_file(), f"marker {marker_file} must not be unlinked by storage cleanup"
            assert marker_file.read_text(encoding="utf-8") == marker_content


def test_p6_r12_structural_absence_and_non_reachability():
    """R12 Section 4.2: Retired runs/PID cleanup functions are structurally absent and absent from AST."""
    import inspect
    from mdstats.training_data import _campaign_cli_core as cli_core

    # 1. Structural absence of deleted functions
    assert not hasattr(cli_core, "_cleanup_obsolete_training_runtimes")
    assert not hasattr(cli_core, "_active_training_run_ids")
    assert not hasattr(cli_core, "_pid_alive")
    assert not hasattr(cli_core, "_diagnostic_log_tail")
    assert not hasattr(cli_core, "_write_cleanup_diagnostic")
    assert not hasattr(cli_core, "_cleanup_checkpoint_model_caches")

    # 2. The transitional cleanup owner is gone; the successor executor is the
    #    single destructive path and inspects no run tree or process marker.
    assert not hasattr(cli_core, "_campaign_cleanup")
    assert not hasattr(cli_core, "_cleanup_remove")
    from mdstats.training_data.storage import executor as storage_executor
    from mdstats.training_data.storage import owners as storage_owners

    for module in (storage_executor, storage_owners):
        source = inspect.getsource(module)
        assert "paths.runs" not in source
        assert "active_process" not in source
        assert "_active_training_run_ids" not in source
        assert "_cleanup_obsolete_training_runtimes" not in source

    # 3. campaign_execution remains absent
    with pytest.raises(ImportError):
        import mdstats.training_data.campaign_execution  # noqa: F401


def test_p6_r13_sha256_receipt_retention_through_storage_cleanup(tmp_path: Path):
    """R13-A / Section 4: Storage cleanup performs zero acceleration-cache eviction and retains >100,000 SHA-256 receipts."""
    import inspect
    from mdstats.training_data import _campaign_cli_core as cli_core
    from mdstats.training_data._common import (
        _sha256_receipt_connection,
        read_validation_receipt,
        sha256_file_cached,
        write_validation_receipt,
    )

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)

    # 1. Create real files and authenticate them through sha256_file_cached()
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    real_file_1 = sample_dir / "real_1.dat"
    real_file_1.write_bytes(b"real-file-payload-1")
    digest_1 = sha256_file_cached(real_file_1)

    real_file_2 = sample_dir / "real_2.dat"
    real_file_2.write_bytes(b"real-file-payload-2")
    digest_2 = sha256_file_cached(real_file_2)

    # 2. Write representative validation receipts
    write_validation_receipt("test_ns", "a" * 64, "b" * 64)
    write_validation_receipt("test_ns", "c" * 64, "d" * 64)

    # 3. Populate > 100,000 unique synthetic receipt rows in one bounded batch
    conn = _sha256_receipt_connection()
    assert conn is not None
    total_to_insert = 100_050
    rows = [
        (f"/synthetic/path/file_{i}.dat", 1, i, 1024, 1_000_000 + i, 1_000_000 + i, f"{i:064x}")
        for i in range(total_to_insert)
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO receipts(path,device,inode,size,mtime_ns,ctime_ns,sha256) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()

    receipt_count_before = int(conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
    val_count_before = int(conn.execute("SELECT COUNT(*) FROM validation_receipts").fetchone()[0])
    assert receipt_count_before >= 100_050
    assert val_count_before >= 2

    # 4. Invoke public safe and cache cleanup
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "safe", "--apply"]) == 0
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "cache", "--apply"]) == 0

    # 5. Assertions:
    receipt_count_after = int(conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
    val_count_after = int(conn.execute("SELECT COUNT(*) FROM validation_receipts").fetchone()[0])
    assert receipt_count_after == receipt_count_before, (
        f"Storage cleanup must not prune SHA-256 receipts (had {receipt_count_before}, now {receipt_count_after})"
    )
    assert val_count_after == val_count_before, "Storage cleanup must not prune validation receipts"

    # Sentinel row check
    sentinel_row = conn.execute(
        "SELECT sha256 FROM receipts WHERE path=?", ("/synthetic/path/file_0.dat",)
    ).fetchone()
    assert sentinel_row is not None
    assert sentinel_row[0] == f"{0:064x}"

    # Verify public API returns exact cached digests
    assert sha256_file_cached(real_file_1) == digest_1
    assert sha256_file_cached(real_file_2) == digest_2
    assert read_validation_receipt("test_ns", "a" * 64) == "b" * 64
    assert read_validation_receipt("test_ns", "c" * 64) == "d" * 64

    # 6. Scoped structural assertion
    from mdstats.training_data.storage import executor as storage_executor

    cleanup_src = inspect.getsource(storage_executor)
    compact_src = inspect.getsource(cli_core.CampaignStore.compact)
    assert "prune_sha256_receipts" not in cleanup_src
    assert "prune_sha256_receipts" not in compact_src


def test_p6_r13_orphan_record_positive_reclamation_and_referenced_record_retention(tmp_path: Path):
    """R13-B / Section 5: Real CampaignStore external pointer is retained while old unreferenced sibling is reclaimed."""
    from mdstats.training_data._campaign_cli_core import (
        EXTERNAL_RECORD_POINTER_SCHEMA,
        EXTERNAL_RECORD_THRESHOLD_BYTES,
    )

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)

    # 1. Publish real external record (> 4 MiB) through CampaignStore.put_record
    large_payload = {"schema": "custom.large-test.v1", "blob": "a" * (EXTERNAL_RECORD_THRESHOLD_BYTES + 8192)}
    store.put_record("heavy_record", large_payload)

    # Assert that the record was stored as EXTERNAL_RECORD_POINTER_SCHEMA
    with store._connect() as db:
        raw_row = db.execute("SELECT payload FROM records WHERE key='heavy_record'").fetchone()
    assert raw_row is not None
    pointer = json.loads(raw_row[0])
    assert pointer.get("schema") == EXTERNAL_RECORD_POINTER_SCHEMA

    referenced_file = (store.path.parent / Path(pointer["relative_path"])).resolve()
    assert referenced_file.is_file()
    assert referenced_file in store.storage_references()
    assert referenced_file.is_relative_to(store.external_record_directory.resolve())

    # Set referenced external file's mtime older than stale_age_hours (e.g. 48h old)
    old_time = time.time() - 48.0 * 3600.0
    os.utime(referenced_file, (old_time, old_time))
    os.utime(referenced_file.parent, (old_time, old_time))

    # 2. Create a separate unreferenced sibling artifact under external_record_directory, also older than grace window
    sibling_dir = store.external_record_directory / "unreferenced_sibling_dir"
    sibling_dir.mkdir(parents=True, exist_ok=True)
    sibling_file = sibling_dir / "unreferenced_file.bin"
    sibling_file.write_bytes(b"orphan-payload-data")
    os.utime(sibling_file, (old_time, old_time))
    os.utime(sibling_dir, (old_time, old_time))

    # Close store reference
    del store

    # 3. Invoke public safe cleanup and cache cleanup
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "safe", "--apply"]) == 0
    assert cli.main(["--config", str(config), "storage", "cleanup", "--tier", "cache", "--apply"]) == 0

    # 4. Assertions:
    # - The old referenced external file remains intact
    assert referenced_file.is_file(), "old referenced external record must be retained by safe/cache cleanup"
    reopened_store = cli.CampaignStore(paths.state_db)
    restored_payload = reopened_store.get_payload("heavy_record")
    assert restored_payload == large_payload

    # - The old unreferenced sibling artifact is reclaimed
    assert not sibling_dir.exists(), "old unreferenced sibling artifact must be reclaimed by safe cleanup"


def test_p6_r12_storage_report_read_only_and_no_retired_stor_policy(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """R12 Section 4 / R11-C / R11-D: storage report contains no retired STOR policy strings, neutral stdout, and is read-only."""
    from mdstats.training_data.storage_accounting import (
        build_campaign_storage_report,
        configured_protected_inputs,
    )

    config, _workspace = build_selected_campaign(tmp_path)
    cfg, paths = cli._load_config(config)

    # Populate representative directories
    (paths.internal / "evaluation-graphs").mkdir(parents=True, exist_ok=True)
    (paths.internal / "evaluation-graphs" / "g.bin").write_bytes(b"graph")

    (paths.internal / "frame-cache").mkdir(parents=True, exist_ok=True)
    (paths.internal / "frame-cache" / "f.bin").write_bytes(b"frames")

    (paths.runs / "run-x" / "checkpoint-model-cache").mkdir(parents=True, exist_ok=True)
    (paths.runs / "run-x" / "checkpoint-model-cache" / "m.pt").write_bytes(b"model")

    (paths.internal / "content-store" / "sha256" / "ab").mkdir(parents=True, exist_ok=True)
    (paths.internal / "content-store" / "sha256" / "ab" / "obj").write_bytes(b"content")

    (paths.internal / "cold-archive").mkdir(parents=True, exist_ok=True)
    (paths.internal / "cold-archive" / "arc.tar.gz").write_bytes(b"archive")

    # Real CLI invocation checks stdout heading
    rc = cli.main(["--config", str(config), "storage", "report"])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert "STOR1" not in stdout
    assert "Campaign storage report (owner-driven, read-only)" in stdout

    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
    )
    payload = report.to_dict()
    payload_str = json.dumps(payload)

    retired_strings = [
        "STOR1",
        "stor2_",
        "stor3_",
        "stor5_",
        "compact_after_protocol_freeze",
        "compact_nonselected_after_protocol_freeze",
        "compact_after_production_export",
        "protocol_freeze",
        "cache_candidate_owner_guard_required",
    ]
    for retired in retired_strings:
        assert retired not in payload_str, f"retired string {retired!r} found in storage report: {payload_str}"

    families = {item["family"]: item for item in payload["families"]}
    # Physical accounting never grants authority: an owner decides, never a family.
    assert families["checkpoint_model_cache"]["manual_reclamation_eligibility"] == "owner_decided"
    assert families["checkpoint_model_cache"]["automatic_reclamation_eligibility"] == "prohibited"
    assert families["frame-cache"]["manual_reclamation_eligibility"] == "owner_decided"
    assert families["frame-cache"]["automatic_reclamation_eligibility"] == "prohibited"

    assert payload["destructive_actions_performed"] is False
    assert (paths.internal / "evaluation-graphs" / "g.bin").is_file()

