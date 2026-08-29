"""P4-E acceptance: terminal projection derivation and reload validation,
section 8 invalidation classification, terminal scientific failure versus
operational interruption, and fresh-process replay.

Terminal claims run against real `CampaignStore` SQLite, real P2 owners, and
the real P3 resolver. Nothing persisted is trusted: every terminal assertion
re-derives from authenticated state.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from tests.test_mlff_target_size_p3a9_head_pointer_reconciliation import (
    _env,
    _execute_boundary,
)

from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data._common import digest
from mdstats.training_data.campaign_target_size_adoption import (
    TargetSizeAdoptionCorruptionError,
    adopt_reconciled_execution_head,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeCampaignState,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
    load_target_size_campaign_revision,
)
from mdstats.training_data.campaign_target_size_terminal import (
    SCIENTIFIC_IDENTITY_FIELDS,
    TargetSizeTerminalProjectionError,
    classify_target_size_invalidation,
    commit_terminal_projection,
    derive_terminal_projection,
    validate_terminal_projection,
)
from mdstats.training_data.target_size_execution import (
    TargetSizeExecutionResolver,
    commit_target_size_boundary_batch,
)
from mdstats.training_data.target_size_experiment import ReducerStatus


def _terminal_campaign(tmp_path: Path):
    """Drive the real production screen to a terminal P2 outcome."""

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
    return config, workspace, harness


def _state_db(workspace: Path) -> Path:
    return workspace / ".mdstats" / "campaign.sqlite3"


def _definition(config: Path):
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.campaign_target_size_runtime import (
        build_current_target_size_authorities,
    )

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        authorities = build_current_target_size_authorities(cfg, paths, store)
    finally:
        store.close()
    return authorities.aggregate.definition, paths


# --- REQ1 terminal success is a re-derived projection ----------------------


def test_p4e_req1_terminal_selection_is_derived_and_revalidated(tmp_path: Path):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    definition, paths = _definition(config)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        terminal = revision.state.terminal
        assert terminal is not None
        assert revision.state.lifecycle in (
            TargetSizeLifecycle.TERMINAL_SELECTED,
            TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
        )
        assert terminal.experiment_definition_digest == definition.content_digest
        assert terminal.execution_head_digest == (
            revision.state.adopted_execution_head_digest
        )
        assert terminal.reducer_state_digest == (
            revision.state.adopted_reducer_state_digest
        )
        if terminal.is_selection:
            # The exact T_selected identity is what P2 produces for that N.
            assert terminal.selected_membership_digest == (
                definition.training_order.candidate_digest(terminal.selected_target_size)
            )
            assert terminal.selected_target_size in (
                definition.qualified_candidate_sizes
            )

        resolver = TargetSizeExecutionResolver(
            workspace / revision.state.execution_root
        )
        head = validate_terminal_projection(
            revision, resolver=resolver, definition=definition
        )
        assert head.content_digest == terminal.execution_head_digest
    finally:
        store.close()


def test_p4e_req1_fresh_process_reload_re_derives_the_identical_projection(
    tmp_path: Path,
):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    definition, _paths = _definition(config)

    # A completely fresh store handle, as a new process would open.
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        resolver = TargetSizeExecutionResolver(
            workspace / revision.state.execution_root
        )
        head = validate_terminal_projection(
            revision, resolver=resolver, definition=definition
        )
        assert (
            derive_terminal_projection(head, definition=definition)
            == revision.state.terminal
        )
    finally:
        store.close()


def test_p4e_req1_repeating_select_target_size_stays_terminal(tmp_path: Path, capsys):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    capsys.readouterr()
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
    # A terminal result is a result, not an interruption: nothing was retrained.
    assert harness.rungs == []
    output = capsys.readouterr().out
    assert "already selected and frozen" in output or "scientifically terminal" in output


# --- REQ2 tamper negatives -------------------------------------------------


def _tampered_terminal(revision, **changes):
    return replace(revision.state.terminal, **changes)


def test_p4e_req2_mutating_only_selected_n_is_rejected(tmp_path: Path):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    definition, _paths = _definition(config)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        terminal = revision.state.terminal
        if not terminal.is_selection:
            pytest.skip("bounded fixture reached a terminal scientific failure")
        other = next(
            size
            for size in definition.qualified_candidate_sizes
            if size != terminal.selected_target_size
        )
        forged = replace(revision.state, terminal=_tampered_terminal(
            revision, selected_target_size=int(other)
        ))
        forged_revision = replace(revision, state=forged)
        resolver = TargetSizeExecutionResolver(
            workspace / revision.state.execution_root
        )
        with pytest.raises(TargetSizeTerminalProjectionError) as excinfo:
            validate_terminal_projection(
                forged_revision, resolver=resolver, definition=definition
            )
        assert "never accepted from campaign state alone" in str(excinfo.value)
    finally:
        store.close()


def test_p4e_req2_mutating_only_t_selected_identity_is_rejected(tmp_path: Path):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    definition, _paths = _definition(config)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        if not revision.state.terminal.is_selection:
            pytest.skip("bounded fixture reached a terminal scientific failure")
        forged = replace(
            revision.state,
            terminal=_tampered_terminal(
                revision, selected_membership_digest=digest({"forged": "membership"})
            ),
        )
        resolver = TargetSizeExecutionResolver(
            workspace / revision.state.execution_root
        )
        with pytest.raises(TargetSizeTerminalProjectionError):
            validate_terminal_projection(
                replace(revision, state=forged),
                resolver=resolver,
                definition=definition,
            )
    finally:
        store.close()


def test_p4e_req2_mutating_only_the_adopted_head_reference_is_rejected(
    tmp_path: Path,
):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    definition, _paths = _definition(config)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        forged = replace(
            revision.state,
            adopted_execution_head_digest=digest({"forged": "head"}),
            terminal=_tampered_terminal(
                revision, execution_head_digest=digest({"forged": "head"})
            ),
        )
        resolver = TargetSizeExecutionResolver(
            workspace / revision.state.execution_root
        )
        with pytest.raises(TargetSizeAdoptionCorruptionError):
            validate_terminal_projection(
                replace(revision, state=forged),
                resolver=resolver,
                definition=definition,
            )
    finally:
        store.close()


def test_p4e_req2_reducer_state_carrying_a_foreign_membership_is_rejected(
    tmp_path: Path,
):
    """A terminal reducer state whose T_selected the training order does not
    produce is rejected at derivation, not persisted."""

    config, workspace, _harness = _terminal_campaign(tmp_path)
    definition, _paths = _definition(config)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        if not revision.state.terminal.is_selection:
            pytest.skip("bounded fixture reached a terminal scientific failure")
        resolver = TargetSizeExecutionResolver(
            workspace / revision.state.execution_root
        )
        from mdstats.training_data.campaign_target_size_adoption import (
            load_adopted_execution_head,
        )

        head = load_adopted_execution_head(resolver, revision)
        forged_state = replace(
            head.post_state,
            selected_membership_digest=digest({"forged": "membership"}),
        )
        forged_head = replace(
            head,
            post_state=forged_state,
            post_state_digest=forged_state.content_digest,
        )
        with pytest.raises(TargetSizeTerminalProjectionError) as excinfo:
            derive_terminal_projection(forged_head, definition=definition)
        assert "the P2 training order does not produce" in str(excinfo.value)
    finally:
        store.close()


def test_p4e_req2_nonterminal_head_cannot_be_projected(tmp_path: Path):
    env = _env(tmp_path, root_name="screen_nonterminal")
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    batch = _execute_boundary(env, tmp_path, state, 1)
    head = commit_target_size_boundary_batch(env["root"], definition, state, batch)
    assert not head.post_state.is_terminal
    with pytest.raises(TargetSizeTerminalProjectionError) as excinfo:
        derive_terminal_projection(head, definition=definition)
    assert "requires a terminal reducer state" in str(excinfo.value)


# --- REQ3 scientific invalidation -----------------------------------------


def _identity(state) -> dict[str, str]:
    return {name: getattr(state, name) for name in SCIENTIFIC_IDENTITY_FIELDS}


@pytest.mark.parametrize("field", SCIENTIFIC_IDENTITY_FIELDS)
def test_p4e_req3_any_changed_scientific_authority_requires_a_fresh_generation(
    tmp_path: Path, field: str
):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        observed = _identity(revision.state)
        assert classify_target_size_invalidation(
            revision.state, observed
        ).is_current

        changed = dict(observed)
        changed[field] = digest({"changed": field})
        result = classify_target_size_invalidation(revision.state, changed)
        assert result.disposition == "fresh_generation"
        assert result.changed_fields == (field,)
        assert field in result.detail
        assert "never reinterpreted" in result.detail
    finally:
        store.close()


def test_p4e_req3_changed_identity_advances_the_generation_and_keeps_the_old_result(
    tmp_path: Path,
):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    from mdstats.training_data.campaign_target_size_cutover import (
        ensure_current_target_size_authorities,
    )

    store = CampaignStore(_state_db(workspace))
    try:
        before = load_target_size_campaign_revision(store)
        changed = _identity(before.state)
        changed["policy_digest"] = digest({"changed": "policy"})
        after = ensure_current_target_size_authorities(store, changed)
        assert after.state.generation == before.state.generation + 1
        # The fresh generation starts without inheriting the retired result.
        assert after.state.terminal is None
        assert after.state.adopted_execution_head_digest is None
        assert after.state.attempt is None
        assert after.state.disposition == "scientific_identity_changed"
        # The retired generation's terminal evidence remains in the chain as
        # history rather than being edited into the new one.
        assert before.state.terminal is not None
    finally:
        store.close()


def test_p4e_req3_equal_selected_n_alone_does_not_prove_equivalence(tmp_path: Path):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        changed = _identity(revision.state)
        changed["aggregate_digest"] = digest({"changed": "aggregate"})
        result = classify_target_size_invalidation(revision.state, changed)
        # The selected size is unchanged in this comparison and is irrelevant.
        assert result.disposition == "fresh_generation"
    finally:
        store.close()


def test_p4e_req3_cv_only_and_production_only_settings_are_target_size_neutral(
    tmp_path: Path,
):
    """Cross-validation and production-only configuration cannot change any
    target-size scientific identity, so they can never invalidate a result."""

    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.campaign_target_size_runtime import (
        build_current_target_size_authorities,
    )

    config, workspace, _harness = _terminal_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        baseline = build_current_target_size_authorities(cfg, paths, store).identity

        neutral = json.loads(json.dumps(cfg))
        neutral.setdefault("partition", {})["cross_validation_seed"] = 987654
        neutral.setdefault("evaluation", {})["checkpoint_strategy"] = "topk"
        neutral.setdefault("production", {})["horizon_epochs"] = 512
        neutral.setdefault("cv", {})["folds"] = 7
        observed = build_current_target_size_authorities(
            neutral, paths, store
        ).identity
        assert observed == baseline

        revision = load_target_size_campaign_revision(store)
        assert classify_target_size_invalidation(
            revision.state, observed
        ).is_current
        # ...and the terminal result is untouched.
        assert revision.state.terminal is not None
    finally:
        store.close()


def test_p4e_req3_target_size_policy_change_does_invalidate(tmp_path: Path):
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.campaign_target_size_runtime import (
        build_current_target_size_authorities,
    )

    config, workspace, _harness = _terminal_campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        baseline = build_current_target_size_authorities(cfg, paths, store).identity
        changed_cfg = json.loads(json.dumps(cfg))
        changed_cfg["training"]["seeds"] = [3, 4]
        changed = build_current_target_size_authorities(
            changed_cfg, paths, store
        ).identity
        assert changed != baseline
        revision = load_target_size_campaign_revision(store)
        result = classify_target_size_invalidation(revision.state, changed)
        assert result.disposition == "fresh_generation"
        assert "policy_digest" in result.changed_fields
    finally:
        store.close()


def test_p4e_req3_classification_requires_the_complete_identity(tmp_path: Path):
    config, workspace, _harness = _terminal_campaign(tmp_path)
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        partial = _identity(revision.state)
        partial.pop("policy_digest")
        with pytest.raises(Exception) as excinfo:
            classify_target_size_invalidation(revision.state, partial)
        assert "complete scientific identity" in str(excinfo.value)
    finally:
        store.close()


# --- REQ4 terminal scientific failure versus operational interruption ------


def test_p4e_req4_operational_interruption_stays_resumable(tmp_path: Path, capsys):
    config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0

    class _Interrupting(p4d._BoundedNumericalHarness):
        def __init__(self, limit: int) -> None:
            super().__init__()
            self._limit = limit

        def train(self, request):
            if len(self.rungs) >= self._limit:
                raise RuntimeError("simulated process death mid-screen")
            return super().train(request)

    interrupted = _Interrupting(limit=3)
    with pytest.raises(RuntimeError):
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=interrupted.train,
            _external_inference_evaluator=interrupted.evaluate,
        )

    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        # An incomplete rung is an operational interruption, never a terminal
        # scientific outcome.
        assert revision.state.terminal is None
        assert revision.state.lifecycle is TargetSizeLifecycle.SCREEN_ACTIVE
    finally:
        store.close()

    resumed = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=resumed.train,
            _external_inference_evaluator=resumed.evaluate,
        )
        == 0
    )
    store = CampaignStore(_state_db(workspace))
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.terminal is not None
    finally:
        store.close()


def test_p4e_req4_terminal_scientific_failure_is_not_an_interruption():
    """A nonconverged terminal outcome persists as a scientific result."""

    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeTerminalProjection,
    )

    projection = TargetSizeTerminalProjection(
        reducer_status=ReducerStatus.NONCONVERGED_AT_CONFIGURED_CEILING.value,
        experiment_definition_digest=digest({"fixture": "definition"}),
        reducer_state_digest=digest({"fixture": "reducer"}),
        execution_head_digest=digest({"fixture": "head"}),
        training_order_digest=digest({"fixture": "order"}),
        terminal_reason_codes=("configured_ceiling",),
    )
    assert not projection.is_selection
    state = TargetSizeCampaignState(
        regime=TargetSizeRegime.CURRENT,
        generation=1,
        lifecycle=TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
        frame_authority_digest=digest({"fixture": "frame"}),
        neutral_statistical_base_digest=digest({"fixture": "neutral"}),
        split_exclusion_digest=digest({"fixture": "split"}),
        policy_digest=digest({"fixture": "policy"}),
        experiment_definition_digest=digest({"fixture": "definition"}),
        aggregate_digest=digest({"fixture": "aggregate"}),
        execution_context_digest=digest({"fixture": "context"}),
        common_preparation_digest=digest({"fixture": "common"}),
        screen_window_digest=digest({"fixture": "window"}),
        execution_root="target-size/g1",
        adopted_execution_head_digest=digest({"fixture": "head"}),
        adopted_reducer_state_digest=digest({"fixture": "reducer"}),
        terminal=projection,
    )
    assert state.lifecycle is TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE
    # A terminal scientific outcome can never be relabelled as a selection.
    from mdstats.training_data._common import TrainingDataInputError

    with pytest.raises(TrainingDataInputError):
        replace(state, lifecycle=TargetSizeLifecycle.TERMINAL_SELECTED)


# --- REQ5 raw/live/EMA restart semantics stay with the P3 owner ------------


def test_p4e_req5_runtime_never_reinterprets_checkpoint_state(tmp_path: Path):
    """P4 code contains no evaluation-state decision; it belongs to P3."""

    import ast
    import re

    training_data = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"
    forbidden_identifiers = {
        "EVALUATION_MODEL_STATE_EMA",
        "EVALUATION_MODEL_STATE_LIVE",
        "target_size_evaluation_model_state",
        "ema",
        "ema_decay",
        "live_parameters",
        "raw_checkpoint_sha256",
    }
    for name in (
        "campaign_target_size_runtime.py",
        "campaign_target_size_state.py",
        "campaign_target_size_cutover.py",
        "campaign_target_size_adoption.py",
        "campaign_target_size_terminal.py",
        "campaign_target_size_retention.py",
        "campaign_target_size_view.py",
    ):
        text = (training_data / name).read_text(encoding="utf-8")
        tree = ast.parse(text)
        identifiers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                identifiers.update(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", node.value))
        offending = forbidden_identifiers & identifiers
        # The runtime translates P3's candidate configuration for MACE, which
        # legitimately carries the optimizer's own EMA keys; nothing there
        # decides which state is canonical.
        if name == "campaign_target_size_runtime.py":
            offending -= {"ema", "ema_decay"}
        assert not offending, (name, sorted(offending))


def test_p4e_req5_resume_goes_through_the_real_p3_owner(tmp_path: Path, monkeypatch):
    """Continuation rungs resolve their predecessor through the P3 owner, so a
    malformed EMA/live checkpoint state is rejected by that owner."""

    import mdstats.training_data.campaign_target_size_runtime as runtime

    config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    calls: list[tuple[int, int, int]] = []
    import mdstats.training_data.target_size_execution as p3

    real = p3.resolve_target_size_candidate_for_resume

    def watching(root, authority, **kwargs):
        calls.append(
            (
                int(kwargs["boundary_epoch"]),
                int(kwargs["target_size"]),
                int(kwargs["optimizer_seed"]),
            )
        )
        return real(root, authority, **kwargs)

    monkeypatch.setattr(p3, "resolve_target_size_candidate_for_resume", watching)
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
    assert calls, "no continuation rung resolved through the real P3 resume owner"
    assert all(boundary > 1 for boundary, _size, _seed in calls)
