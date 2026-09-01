"""P4-F acceptance: promoted P3 evidence in the real storage owners, the
section 10.5 storage acceptance, public documentation truthfulness, and the
section 16 structural closure checks.

Storage claims run through the real `build_campaign_storage_report`, the real
`CampaignOwnershipBoundary` destructive authorization, and the real cleanup
owner - never a test-local retention flag.
"""

from __future__ import annotations

import ast
import json
import os
import time
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)
from mdstats.training_data.storage_accounting import (
    ArtifactRetentionClass,
    build_campaign_storage_report,
    configured_protected_inputs,
)

_REPO = Path(__file__).resolve().parents[1]
_TRAINING_DATA = _REPO / "mdstats" / "training_data"
_GUIDE = _REPO / "docs" / "guides" / "mlff_campaign_cli_user_guide.md"

_TARGET_SIZE_FAMILIES = {
    "target_size_execution_graph",
    "target_size_boundary_snapshots",
    "target_size_training_runtime",
    "target_size_candidate_materializations",
    "target_size_evaluation_evidence",
    "target_size_failure_evidence",
    "target_size_execution_bulk",
}


def _safe_cleanup(cfg, paths, store) -> dict:
    """Apply the real owner-driven safe tier through its production owner."""

    from types import SimpleNamespace

    from mdstats.training_data.storage import commands as storage_commands

    boundary = cli._campaign_ownership_boundary(cfg, paths, store)
    context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
    return storage_commands.storage_cleanup(
        context, SimpleNamespace(tier="safe", apply=True, dry_run=False)
    )


def _screened_campaign(tmp_path: Path):
    config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    harness = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    return config, workspace


def _boundary_for(config: Path):
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    return cfg, paths, store, cli._campaign_ownership_boundary(cfg, paths, store)


# --- REQ1 promoted P3 bytes appear in storage accounting -------------------


def test_p4f_req1_storage_report_accounts_promoted_target_size_families(
    tmp_path: Path,
):
    config, workspace = _screened_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
        largest_limit=50,
    )
    families = {item.family: item for item in report.families}
    present = _TARGET_SIZE_FAMILIES & set(families)
    assert present, sorted(families)
    assert "target_size_execution_graph" in present
    assert sum(families[name].logical_bytes for name in present) > 0
    for name in present:
        record = families[name]
        assert record.automatic_reclamation_eligibility == "prohibited", name
        assert record.manual_reclamation_eligibility == "prohibited", name
        assert record.retention_class in {
            ArtifactRetentionClass.RESTART_CRITICAL.value,
            ArtifactRetentionClass.EVALUATION_CAPSULE.value,
            ArtifactRetentionClass.PROTECTED_DIAGNOSTIC.value,
        }, name
    # The promoted evidence is not silently pooled into the generic bucket.
    assert "internal_campaign_artifacts" not in present


def test_p4f_req1_storage_command_reports_target_size_bytes(tmp_path: Path):
    from types import SimpleNamespace

    config, workspace = _screened_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    # The owner-driven report attributes the bytes to the real P3 owner.
    assert cli.command_storage(
        SimpleNamespace(config=str(config), top=50, deep=False)
    ) == 0
    payload = json.loads(
        (paths.results / "storage-report.json").read_text(encoding="utf-8")
    )
    owners = {item["owner"] for item in payload["owner_families"]}
    assert "p3" in owners
    assert payload["destructive_actions_performed"] is False
    assert payload["grants_mutation_authority"] is False

    # The explicit deep audit still reports the physical path families.
    assert cli.command_storage(
        SimpleNamespace(config=str(config), top=50, deep=True)
    ) == 0
    deep = json.loads(
        (paths.results / "storage-deep-audit.json").read_text(encoding="utf-8")
    )
    families = {item["family"] for item in deep["families"]}
    assert _TARGET_SIZE_FAMILIES & families
    assert deep["destructive_actions_performed"] is False


# --- REQ2 safe cleanup preserves restart and reconciliation capability -----


def test_p4f_req2_safe_cleanup_preserves_the_execution_root(tmp_path: Path):
    config, workspace = _screened_campaign(tmp_path)
    cfg, paths, store, _boundary = _boundary_for(config)
    try:
        revision = load_target_size_campaign_revision(store)
        root = workspace / revision.state.execution_root
        before = {
            path: path.stat().st_size
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }
        assert before

        old = time.time() - 30 * 86_400
        for path in list(before):
            os.utime(path, (old, old))

        payload = _safe_cleanup(cfg, paths, store)
        after = {
            path: path.stat().st_size
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }
        assert after == before, sorted(set(before) - set(after))
        assert not any(
            str(root) in str(action["path"])
            for action in payload["execution"]["completed_actions"]
        )
    finally:
        store.close()


def test_p4f_req2_fresh_process_replay_after_safe_cleanup_is_identical(
    tmp_path: Path,
):
    config, workspace = _screened_campaign(tmp_path)
    cfg, paths, store, _boundary = _boundary_for(config)
    try:
        before = load_target_size_campaign_revision(store)
        _safe_cleanup(cfg, paths, store)
    finally:
        store.close()

    reopened = CampaignStore(paths.state_db)
    try:
        after = load_target_size_campaign_revision(reopened)
        assert after == before
        assert after.state.terminal == before.state.terminal
    finally:
        reopened.close()

    # A fresh invocation re-derives the identical result and retrains nothing.
    harness = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    assert harness.rungs == []


def test_p4f_req2_manual_cache_tier_cannot_reclaim_target_size_evidence(
    tmp_path: Path,
):
    config, workspace = _screened_campaign(tmp_path)
    cfg, paths, store, boundary = _boundary_for(config)
    try:
        revision = load_target_size_campaign_revision(store)
        root = workspace / revision.state.execution_root
        old = time.time() - 30 * 86_400
        candidates = [path for path in sorted(root.rglob("*")) if path.is_file()]
        for path in candidates:
            os.utime(path, (old, old))
        denied = 0
        for path in candidates:
            authorized, detail = boundary.destructive_authorization(path)
            if not authorized:
                denied += 1
                assert "target-size" in detail or "retained" in detail
        assert denied == len(candidates), (denied, len(candidates))
    finally:
        store.close()


def test_p4f_req2_external_and_symlink_paths_stay_denied(tmp_path: Path):
    config, workspace = _screened_campaign(tmp_path)
    cfg, paths, store, boundary = _boundary_for(config)
    try:
        external = tmp_path / "outside"
        external.mkdir(exist_ok=True)
        authorized, detail = boundary.destructive_authorization(external)
        assert not authorized
        assert "outside the campaign workspace" in detail

        escape = paths.workspace / "escape"
        if not escape.exists():
            escape.symlink_to(external, target_is_directory=True)
        authorized, _detail = boundary.destructive_authorization(escape / "child")
        assert not authorized
    finally:
        store.close()


# --- REQ3 documentation describes the actual lifecycle ---------------------


def test_p4f_req3_user_guide_states_prepare_does_not_select():
    text = " ".join(_GUIDE.read_text(encoding="utf-8").split())
    assert "`prepare` does not select a target size" in text
    assert "only current screening entrypoint" in text
    assert "quarantines them rather than migrating them" in text
    assert "not editable fields" in text


def test_p4f_req3_user_guide_does_not_claim_a_retired_lifecycle():
    text = " ".join(_GUIDE.read_text(encoding="utf-8").split())
    # The guide must not still promise that prepare builds the screening
    # candidate matrix or that materialize realizes a selected-size topology.
    assert "writes the complete qualified-size x screening-seed DATA8 candidate matrix" not in text
    assert "`materialize` is valid only after `N*` is frozen." not in text
    assert "storage` is an orthogonal artifact-management command" in text
    # Post-production qualification is now implemented, so the guide describes
    # it as a downstream *consumer* of the frozen product rather than as an
    # unimplemented obligation - and still never as a selector.
    assert "Post-production qualification of the finished product is a separate" in text
    assert "It never creates, reorders, or shrinks that publication" in text
    assert (
        "never selects a different seed, checkpoint, or committee member" in text
    )
    assert "advance` never runs qualification or opens locked evidence" in text


def test_p4f_req3_parser_help_describes_the_current_commands():
    parser = cli.build_parser()
    subcommands = parser._subparsers._group_actions[0]
    by_name = {
        action.dest: action.help for action in subcommands._choices_actions
    }
    assert "does not select a target size" in by_name["prepare"]
    assert (
        "only command that trains candidates and decides N"
        in by_name["select-target-size"]
    )
    assert "post-selection cross-validation" in by_name["cross-validate"]
    assert "fresh final production" in by_name["train-production"]
    assert "post-production qualification" in by_name["qualification"]
    # The retired lifecycle commands are absent from the current surface.
    assert not ({"materialize", "preflight", "train", "extend-seed", "evaluate", "verify"} & set(by_name))


def test_p4f_req3_config_example_documents_partition_identity_coupling():
    text = " ".join(
        (_REPO / "campaign.toml.example").read_text(encoding="utf-8").split()
    )
    assert "changes the target-size" in text
    assert "scientific identity" in text
    assert "never invalidate a target-size result" in text


# --- REQ4 structural closure (section 16) ---------------------------------


def _module_source(name: str) -> str:
    return (_TRAINING_DATA / name).read_text(encoding="utf-8")


_P4_MODULES = (
    "campaign_target_size_state.py",
    "campaign_target_size_cutover.py",
    "campaign_target_size_adoption.py",
    "campaign_target_size_retention.py",
    "campaign_target_size_terminal.py",
    "campaign_target_size_view.py",
    "campaign_target_size_runtime.py",
)


def test_p4f_req4_no_second_target_size_algorithm_owner():
    """P4 adds no split, reducer, trainer, evaluator, or replay implementation."""

    forbidden_prefixes = (
        "split_target_size",
        "advance_target_size_reducer",
        "qualify_target_size_candidates",
        "build_target_training_order",
        "build_target_evaluation_order",
        "reconcile_target_size_screen_root",
        "apply_complete_boundary_batch",
    )
    for name in _P4_MODULES:
        tree = ast.parse(_module_source(name))
        defined = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        for symbol in defined:
            assert not any(
                symbol.startswith(prefix) for prefix in forbidden_prefixes
            ), (name, symbol)


def test_p4f_req4_no_version_prefixed_production_names():
    for name in _P4_MODULES:
        text = _module_source(name).lower()
        assert "v7_" not in text, name
        assert "_v7" not in text, name


def test_p4f_req4_target_size_study_is_unreachable_from_current_entrypoints():
    """`target_size_study` is not reachable from the current target-size commands."""

    source = _module_source("_campaign_cli_core.py")
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    retired = {
        "_ensure_target_size_study",
        "_load_verified_target_size_study_authority",
        "_load_train2_study_optional",
    }

    def reachable(entry: str, seen: set[str]) -> set[str]:
        if entry in seen or entry not in functions:
            return set()
        seen.add(entry)
        found: set[str] = set()
        for node in ast.walk(functions[entry]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
                if name in retired:
                    found.add(name)
                found |= reachable(name, seen)
        return found

    for entry in ("command_prepare", "command_select_target_size"):
        # The historical non-TRAIN2 branch of `prepare` is out of scope here; it
        # is guarded by the policy-generation check and is removed by the
        # cleanup package.
        seen = {"_execute_prepare_current_authority"}
        assert not reachable(entry, seen), entry


def test_p4f_req4_exactly_one_mutable_current_target_size_authority():
    """One canonical generation authority and one mutable state table."""

    state = ast.parse(_module_source("campaign_target_size_state.py"))
    classes = {
        node.name: node for node in ast.walk(state) if isinstance(node, ast.ClassDef)
    }
    fields = [
        node.target.id
        for node in classes["TargetSizeCampaignState"].body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ]
    assert [name for name in fields if "generation" in name] == ["generation"]

    # Exactly one class anywhere in the P4 surface is a persisted campaign-state
    # aggregate: one that binds a regime, a canonical generation, and a
    # lifecycle. Other classes may carry a read-only expectation or reference,
    # but none may become a second mutable current-state authority.
    aggregates: list[tuple[str, str]] = []
    for name in _P4_MODULES:
        tree = ast.parse(_module_source(name))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            declared = {
                item.target.id
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
            if {"regime", "generation", "lifecycle"} <= declared:
                aggregates.append((name, node.name))
    assert aggregates == [
        ("campaign_target_size_state.py", "TargetSizeCampaignState")
    ], aggregates


def test_p4f_req4_current_head_pointer_is_not_campaign_authority():
    """No P4 module reads the P3-local recovery pointer as campaign authority."""

    for name in _P4_MODULES:
        text = _module_source(name)
        assert "CURRENT_HEAD_FILENAME" not in text, name
        assert "current_head.json" not in text or "rebuildable" in text, name


def test_p4f_req4_no_current_domain_or_pre_target_cv_authority():
    forbidden = (
        "domain_prefix_digests",
        "label_domain_id",
        "compatibility_domain",
        "mlcv_role_catalog",
        "cross_validation_folds",
        "complement",
    )
    for name in _P4_MODULES:
        text = _module_source(name)
        for token in forbidden:
            assert token not in text, (name, token)


def test_p4f_req4_no_reverse_nested_lock_or_transaction_path():
    """Section 6.3: no campaign transaction wraps P3 or STOR mutation."""

    forbidden = {
        "reconcile_target_size_screen_root",
        "reconcile_and_adopt_target_size_head",
        "commit_target_size_boundary_batch",
        "record_candidate_boundary_outcome",
        "resolve_target_size_candidate_for_resume",
        "_remove_durably",
        "durable_unlink",
        "deduplicate",
        "create_cold_archive",
        "restore_cold_archive",
        "rmtree",
        "unlink",
        "flock",
    }
    for name in _P4_MODULES:
        tree = ast.parse(_module_source(name))
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            if not any(
                "exclusive_transaction" in ast.dump(item.context_expr)
                for item in node.items
            ):
                continue
            called = set()
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call):
                    if isinstance(inner.func, ast.Attribute):
                        called.add(inner.func.attr)
                    elif isinstance(inner.func, ast.Name):
                        called.add(inner.func.id)
            assert not (called & forbidden), (name, sorted(called & forbidden))


def test_p4f_req4_every_destructive_production_path_carries_the_fence():
    """No production destructive path builds an unfenced ownership boundary.

    `command_storage` is the one exception and is read-only by contract.
    """

    source = _module_source("_campaign_cli_core.py")
    tree = ast.parse(source)
    constructions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "CampaignOwnershipBoundary"
    ]
    # Exactly one construction site remains, inside the shared helper.
    assert len(constructions) == 1
    helper = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_campaign_ownership_boundary"
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_target_size_retention_fence"
        for node in ast.walk(helper)
    )
