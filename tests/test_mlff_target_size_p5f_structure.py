"""P5-F acceptance: structural and absence evidence for the current path.

Runtime tests can show that the right thing happens; they cannot show that a
wrong path is absent. These checks read the source of the current post-selection
modules and the CLI to prove that retired authority is not merely unused but
unreachable, and that P5 introduced no second current-state owner and no
version-prefixed production naming.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

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


_SCREENING_CONTINUATION_SEEDS = frozenset(
    {
        "resolve_target_size_candidate_for_resume",
        "TargetSizeContinuationRequest",
        "continuation_request_from_boundary",
        "build_target_size_candidate_trajectory",
        "promote_target_size_boundary_snapshot",
    }
)


def _screening_continuation_owner_closure() -> frozenset[str]:
    """Top-level target-size definitions that are, or route to, continuation owners.

    A renamed wrapper around a screening-continuation owner stays in this set
    because membership follows references, not spelling.
    """

    references: dict[str, set[str]] = {}
    for path in (_TRAINING_DATA / "target_size_execution").glob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                references[node.name] = {
                    item.id for item in ast.walk(node) if isinstance(item, ast.Name)
                } | {
                    item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)
                }
    closure = set(_SCREENING_CONTINUATION_SEEDS)
    while True:
        added = {
            name for name, refs in references.items() if name not in closure and refs & closure
        }
        if not added:
            return frozenset(closure)
        closure |= added


def _continuation_edges(source: str, owners: frozenset[str]) -> list[str]:
    edges: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            edges.extend(alias.name for alias in node.names if alias.name in owners)
        elif isinstance(node, ast.Attribute) and node.attr in owners:
            edges.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in owners:
            edges.append(node.id)
    return edges


def test_p5f_continuation_closure_rule_detects_renamed_and_attribute_routes():
    owners = _screening_continuation_owner_closure()
    assert _SCREENING_CONTINUATION_SEEDS <= owners
    # Real screening recovery routes are in the closure by reference.
    assert "recover_authenticated_boundary_progress" in owners
    assert "initial_target_size_continuation_request" in owners
    assert _continuation_edges(
        "from .target_size_execution import initial_target_size_continuation_request as fresh\n",
        owners,
    )
    assert _continuation_edges(
        "from . import target_size_execution as tse\n"
        "def f(x):\n    return tse.resolve_target_size_candidate_for_resume(x)\n",
        owners,
    )
    # P5's own authenticated MACE continuation is not a screening owner.
    assert not _continuation_edges(
        "def launch(request, command):\n"
        "    if int(request.start_epoch) > 0:\n"
        "        command.append('--restart_latest')\n",
        owners,
    )


def test_p5f_no_screening_continuation_owner_is_reachable_from_post_selection():
    """Absence: a screening trajectory can never be resumed as a P5 run."""

    owners = _screening_continuation_owner_closure()
    offenders = [
        (name, edge)
        for name, source in _sources().items()
        for edge in _continuation_edges(source, owners)
    ]
    assert not offenders, offenders


def test_p5f_p5_restart_launch_is_bound_to_authenticated_p5_continuation():
    """Positive ownership: P5's ``--restart_latest`` comes only from its own owner.

    The trainer emits the flag only for ``request.start_epoch > 0``, and the
    runtime's only source of that epoch is the authenticated TRAIN2/P5
    continuation owner.
    """

    execution = (_TRAINING_DATA / "post_selection_execution.py").read_text(encoding="utf-8")
    guards = [
        node
        for node in ast.walk(ast.parse(execution))
        if isinstance(node, ast.If)
        and "--restart_latest" in ast.unparse(node)
        and "request.start_epoch" in ast.unparse(node.test)
    ]
    assert len(guards) == 1

    runtime = ast.parse(
        (_TRAINING_DATA / "campaign_post_selection_runtime.py").read_text(encoding="utf-8")
    )
    producers = [
        ast.unparse(node.value)
        for node in ast.walk(runtime)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Tuple)
            and any(isinstance(item, ast.Name) and item.id == "start_epoch" for item in target.elts)
            or isinstance(target, ast.Name) and target.id == "start_epoch"
            for target in node.targets
        )
    ]
    assert producers, producers
    assert all(
        value.startswith("_authenticate_post_selection_continuation(")
        or value == "setup.start_epoch"
        for value in producers
    ), producers


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
    """No generic command can act as a second post-selection scheduler.

    The destructive cutover removed the retired generic lifecycle entirely, so
    the guard is structural: those commands no longer exist to be redirected.
    """

    source = (_TRAINING_DATA / "_campaign_cli_core.py").read_text(encoding="utf-8")
    for name in (
        "command_materialize",
        "command_preflight",
        "command_train",
        "command_extend_seed",
        "command_evaluate",
        "command_verify",
        "_require_post_selection_production_path",
    ):
        assert not re.search(rf"^def {name}\(", source, re.MULTILINE), name
    assert "def command_cross_validate" in source
    assert "def command_train_production" in source


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
