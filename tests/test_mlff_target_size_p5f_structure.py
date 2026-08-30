"""P5-F acceptance: structural and absence evidence for the current path.

Runtime tests can show that the right thing happens; they cannot show that a
wrong path is absent. These checks read the source of the current post-selection
modules and the CLI to prove that retired authority is not merely unused but
unreachable, and that P5 introduced no second current-state owner and no
version-prefixed production naming.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from mdstats.training_data import _campaign_cli_core as cli

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"

_POST_SELECTION_MODULES = (
    "campaign_post_selection.py",
    "campaign_post_selection_runtime.py",
    "post_selection_cv_acceptance.py",
    "post_selection_cv_plan.py",
    "post_selection_execution.py",
    "post_selection_identity.py",
    "post_selection_production.py",
    "post_selection_run_identity.py",
    "post_selection_store.py",
)


def _sources() -> dict[str, str]:
    return {
        name: (_TRAINING_DATA / name).read_text(encoding="utf-8")
        for name in _POST_SELECTION_MODULES
    }


def test_p5f_every_declared_post_selection_module_exists():
    for name in _POST_SELECTION_MODULES:
        assert (_TRAINING_DATA / name).is_file(), name


def test_p5f_no_legacy_data5_or_label_domain_cv_authority_is_reachable():
    offenders: list[tuple[str, str]] = []
    for name, source in _sources().items():
        for marker in (
            "label_domain_id",
            "MlcvRoleCatalog",
            "build_mlcv_role_catalog",
            "cross_validation_plans",
            "build_cross_validation_plans",
            "cv_not_performed",
            "data5",
        ):
            if marker in source:
                offenders.append((name, marker))
    assert not offenders, offenders


def test_p5f_no_replay_weighted_ranking_reaches_the_current_decision_owners():
    offenders: list[tuple[str, str]] = []
    for name, source in _sources().items():
        for marker in (
            "full_score",
            "replay_weight",
            "target_weight",
            "combined_score",
            "MlcvRunSelectionPolicy",
        ):
            if marker in source:
                offenders.append((name, marker))
    assert not offenders, offenders


def test_p5f_no_locked_or_calibration_evidence_reaches_model_control():
    offenders: list[tuple[str, str]] = []
    for name, source in _sources().items():
        for marker in (
            "locked_test",
            "TARGET_LOCKED_TEST",
            "calibration",
            "locked_interpolation",
        ):
            if marker in source:
                offenders.append((name, marker))
    assert not offenders, offenders


def test_p5f_no_post_selection_path_writes_target_size_campaign_state():
    """Absence: P5 cannot mutate the P4 selection, head, reducer, or revision."""

    offenders: list[tuple[str, str]] = []
    for name, source in _sources().items():
        for marker in (
            "commit_target_size_campaign_transition",
            "commit_terminal_projection",
            "TargetSizeTransitionKind",
            "advance_target_size_reducer",
            "adopt_reconciled_execution_head",
        ):
            if marker in source:
                offenders.append((name, marker))
    assert not offenders, offenders


def test_p5f_the_only_campaign_state_write_is_the_fenced_pointer():
    """The store owner is the single place that writes campaign-store rows."""

    writers: list[str] = []
    for name, source in _sources().items():
        if "exclusive_transaction" in source or "INSERT OR REPLACE" in source:
            writers.append(name)
    assert writers == ["post_selection_store.py"], writers

    source = (_TRAINING_DATA / "post_selection_store.py").read_text(encoding="utf-8")
    # The commit-time comparison and the write share one transaction.
    body = source[source.index("def publish_current_post_selection_pointer") :]
    body = body[: body.index("\ndef ")]
    assert "exclusive_transaction" in body
    assert "_current_campaign_revision(db)" in body
    assert "INSERT OR REPLACE INTO meta" in body


def test_p5f_no_target_size_result_json_is_read_as_authority():
    offenders: list[tuple[str, str]] = []
    for name, source in _sources().items():
        for marker in ("target-size-state.json", "TARGET_SIZE_RESULT_VIEW_SCHEMA"):
            if marker in source:
                offenders.append((name, marker))
    assert not offenders, offenders


def test_p5f_no_n3_to_budget_dependency_edge_exists():
    offenders: list[tuple[str, str]] = []
    for name, source in _sources().items():
        for marker in (
            "fidelity_epochs",
            "schedule.n3",
            "build_target_size_screen_schedule",
        ):
            if marker in source:
                offenders.append((name, marker))
    assert not offenders, offenders

    # And the CV budget owner reads only its own configuration table, so it
    # cannot pick up `[training].max_num_epochs` by any route.
    tree = ast.parse(
        (_TRAINING_DATA / "post_selection_identity.py").read_text(encoding="utf-8")
    )
    resolver = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "resolve_cv_validation_policy_identity"
    )
    tables = [
        tuple(
            argument.value
            for argument in node.args[1:]
            if isinstance(argument, ast.Constant)
        )
        for node in ast.walk(resolver)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_table"
    ]
    assert tables == [("post_selection", "cv")], tables


def test_p5f_no_version_prefixed_production_symbols_are_introduced():
    offenders: list[tuple[str, str]] = []
    for name in _POST_SELECTION_MODULES:
        tree = ast.parse((_TRAINING_DATA / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("v7_") or node.name.startswith("V7"):
                    offenders.append((name, node.name))
        assert not name.startswith("v7_")
    assert not offenders, offenders


def test_p5f_public_commands_route_through_the_post_selection_owners():
    parser = cli.build_parser()
    actions = [
        action
        for action in parser._subparsers._group_actions
        if hasattr(action, "choices")
    ]
    choices = set()
    for action in actions:
        choices.update(action.choices)
    assert {"cross-validate", "train-production"} <= choices

    assert cli.command_cross_validate is not None
    assert cli.command_train_production is not None


def test_p5f_generic_train_and_evaluate_point_at_the_post_selection_owners():
    """The generic commands are still not a second post-selection scheduler."""

    source = (_TRAINING_DATA / "_campaign_cli_core.py").read_text(encoding="utf-8")
    guard = source[source.index("def _require_post_selection_production_path") :]
    guard = guard[: guard.index("\ndef ")]
    assert "cross-validate" in guard and "train-production" in guard
    assert "not available in this release" not in guard

    materialize = source[source.index("def command_materialize") :]
    materialize = materialize[: materialize.index("\n_DATA8_VARIANT_RE")]
    assert "cross-validate" in materialize and "train-production" in materialize


def test_p5f_post_selection_modules_import_no_retired_mlcv_topology():
    retired = {
        "mlcv_roles",
        "mlcv_select",
        "mlcv_aggregate",
        "mlcv_final",
        "mlcv_migration",
        "mlcv_verification",
        "mlcv_monitors",
        "data5_bundle",
        "target_data_roles",
    }
    offenders: list[tuple[str, str]] = []
    for name in _POST_SELECTION_MODULES:
        tree = ast.parse((_TRAINING_DATA / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[-1] in retired:
                        offenders.append((name, alias.name))
                continue
            if module in retired:
                offenders.append((name, module))
    assert not offenders, offenders
