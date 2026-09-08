"""Acceptance for the operator-owned target-size design and its freeze.

The automatic screen is no longer the authority that fixes how much target data
downstream training uses.  It is an optional, cached, inspectable diagnostic that
*recommends* a size.  What these tests hold to account is the rest of that
sentence: the operator owns a mutable provisional design until `cross-validate`
admits it, at which point the size, its exact membership, and both role horizons
freeze together.

Every campaign, CampaignStore, P1/P2/P3/P4 and P5 owner here runs as production
code.  Only the expensive MACE numerics sit below the owner boundary, and the
manual path deliberately installs *poison* trainers and evaluators: choosing a
size by hand must not be able to reach a trainer at all.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
import tests._mlff_post_selection_fixture as fx

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore, CampaignCliError
from mdstats.training_data.campaign_post_selection import (
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_target_size_selection import (
    TargetSizeSelectionError,
    resolve_frozen_target_design,
    resolve_frozen_target_selection,
    resolve_provisional_horizons,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    load_target_size_campaign_revision,
)

_TRAINING_DATA = Path(cli.__file__).resolve().parent


class _PoisonTrainer:
    def __call__(self, request):  # pragma: no cover - the point is never reaching it
        raise AssertionError(
            "Manual target-size selection may never train a candidate."
        )


class _PoisonEvaluator:
    def __call__(self, *args, **kwargs):  # pragma: no cover - same
        raise AssertionError(
            "Manual target-size selection may never run an EVAL2 evaluation."
        )


def _prepared(tmp_path: Path):
    """A prepared campaign with no proposal, no diagnostic, nothing frozen."""

    from unittest.mock import patch

    with patch.object(p4d, "_CONFIG", fx.fixture_config_text()):
        config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    return config, workspace


def _revision(config: Path):
    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def _entries(config: Path):
    """The complete ordered provisional design, as authoritative state holds it."""

    return _revision(config).state.provisional_entries


def _sizes(config: Path) -> list[int]:
    return [entry.n_provisional for entry in _entries(config)]


def _only(config: Path):
    """The single provisional entry, asserting the design really has one."""

    entries = _entries(config)
    assert len(entries) == 1, [entry.n_provisional for entry in entries]
    return entries[0]


def _frozen(config: Path):
    return _revision(config).state.frozen_entries


def _select(config: Path, *argv: str) -> int:
    return p4d._run(
        config,
        "select-target-size",
        *argv,
        _external_boundary_trainer=_PoisonTrainer(),
        _external_inference_evaluator=_PoisonEvaluator(),
    )


# --- 19.1 CLI contract ------------------------------------------------------


def test_bare_select_target_size_is_invalid_and_actionable(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    with pytest.raises(CampaignCliError) as excinfo:
        _select(config)
    message = str(excinfo.value)
    assert "select-target-size <N>" in message
    assert "--auto" in message


def test_size_and_auto_are_mutually_exclusive(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    with pytest.raises(CampaignCliError, match="mutually"):
        _select(config, "8", "--auto")


@pytest.mark.parametrize("flag", ["--horizon-cv", "--horizon"])
def test_nonpositive_horizons_are_rejected(tmp_path: Path, flag: str):
    config, _workspace = _prepared(tmp_path)
    with pytest.raises(CampaignCliError, match="positive number of epochs"):
        _select(config, "8", flag, "0")


def test_a_noncandidate_size_is_refused_by_the_p2_owner(tmp_path: Path):
    config, _workspace = _prepared(tmp_path)
    with pytest.raises(TargetSizeSelectionError, match="not a configured qualified"):
        _select(config, "7")
    assert _entries(config) == ()


# --- 19.2 the manual path, end to end, with no screening work at all --------


def test_manual_selection_trains_nothing_and_freezes_only_at_cross_validate(
    tmp_path: Path, capsys
):
    from mdstats.training_data.campaign_lifecycle import project_campaign_lifecycle

    config, _workspace = _prepared(tmp_path)
    assert _select(config, str(fx.SELECTED_TARGET_SIZE)) == 0

    revision = _revision(config)
    proposal = _only(config)
    assert proposal.n_provisional == fx.SELECTED_TARGET_SIZE
    assert proposal.selection_source == "manual"
    # No screen ran, so there is no diagnostic and no adopted P3 head at all.
    assert revision.state.auto_diagnostic is None
    assert revision.state.adopted_execution_head_digest is None
    assert revision.state.frozen_entries is None

    output = capsys.readouterr().out
    assert "Frozen: no" in output

    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        snapshot = project_campaign_lifecycle(paths, store)
        step = snapshot.step("target_size_selection")
        assert step.state == "complete" and "Frozen: no" in step.message
        assert snapshot.next_command == "cross-validate"
    finally:
        store.close()

    # Cross-validation admission is the freeze, and it needs no P3 evidence.
    post = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, post) == 0

    entries = _frozen(config)
    assert entries is not None and len(entries) == 1
    frozen = entries[0]
    assert frozen.n_selected == fx.SELECTED_TARGET_SIZE
    assert frozen.selection_source == "manual"
    assert _entries(config) == ()

    # The real CV owner received the frozen horizon.
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        from mdstats.training_data.campaign_post_selection_runtime import (
            build_post_selection_context,
            resolve_current_cv_plan,
        )

        context = build_post_selection_context(cfg, paths, store, trainer=object())
        assert context.cv_policy.cv_max_num_epochs == frozen.cv_max_num_epochs
        assert (
            context.production_policy.production_max_num_epochs
            == frozen.production_max_num_epochs
        )
        plan = resolve_current_cv_plan(context)
        assert plan is not None
        assert plan.binding.n_selected == fx.SELECTED_TARGET_SIZE
    finally:
        store.close()

    # After the freeze, selection commands refuse rather than mutate.
    with pytest.raises(TargetSizeSelectionError, match="frozen"):
        _select(config, "4")
    with pytest.raises(TargetSizeSelectionError, match="frozen"):
        _select(config, "--auto")


def test_status_offers_both_forms_and_never_prints_the_invalid_bare_command(
    tmp_path: Path, capsys
):
    config, _workspace = _prepared(tmp_path)
    assert cli.main(["--config", str(config), "status"]) == 0
    output = capsys.readouterr().out
    assert "select-target-size <N>" in output
    assert "select-target-size --auto" in output
    # `advance` stops here rather than deciding for the operator.
    assert p4d._run(config, "advance") == 0
    advanced = capsys.readouterr().out
    assert "does not decide it for you" in advanced
    assert _entries(config) == ()

    assert _select(config, "8") == 0
    capsys.readouterr()
    assert cli.main(["--config", str(config), "status"]) == 0
    output = capsys.readouterr().out
    assert "Frozen: no" in output
    assert "cross-validate" in output


def test_a_corrupt_proposal_membership_is_never_admitted(tmp_path: Path):
    """Freeze re-derives membership from P2; a forged proposal fails closed."""

    from dataclasses import replace

    from mdstats.training_data._common import digest
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeTransitionKind,
        commit_target_size_campaign_transition,
    )
    from mdstats.training_data.campaign_target_size_selection import _successor_with

    config, _workspace = _prepared(tmp_path)
    assert _select(config, "8") == 0

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        forged = replace(
            revision.state.provisional_entries[0],
            membership_digest=digest({"forged": "membership"}),
        )
        revision = commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.SET_PROPOSAL,
            expected=revision.expectation(),
            successor=_successor_with(revision.state, provisional_entries=(forged,)),
        ).revision
        with pytest.raises(TargetSizeSelectionError, match="does not reproduce"):
            resolve_frozen_target_design(cfg, paths, store, admit=True)
        # Nothing was frozen by the attempt.
        assert (
            load_target_size_campaign_revision(store).state.frozen_entries is None
        )
    finally:
        store.close()


# --- 19.5 steering ----------------------------------------------------------


def test_the_operator_may_steer_manual_and_automatic_choices_freely(tmp_path: Path):
    """Steering is now collection steering: append, replace in place, override.

    A second distinct N no longer erases the first.  One expensive prepared
    generation is deliberately reusable, so requesting another size must be an
    addition to the requested experiment, not a silent replacement of it.
    """

    config, _workspace = _prepared(tmp_path)

    assert _select(config, "4") == 0
    assert _sizes(config) == [4]

    # A distinct manual N appends rather than replacing.
    assert _select(config, "8") == 0
    assert _sizes(config) == [4, 8]

    # Reselecting an existing N replaces its complete entry in place, keeping
    # its list position.
    assert _select(config, "4", "--horizon-cv", "21") == 0
    assert _sizes(config) == [4, 8]
    assert _entries(config)[0].cv_max_num_epochs == 21
    assert _entries(config)[1].cv_max_num_epochs != 21

    # manual -> auto: the recommendation merges through the same owner. It is
    # already in the design, so it replaces its own entry rather than appending.
    screen = fx._SelectedSizeScreenHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )
    state = _revision(config).state
    assert [entry.n_provisional for entry in state.provisional_entries] == [4, 8]
    recommended = next(
        entry
        for entry in state.provisional_entries
        if entry.n_provisional == fx.SELECTED_TARGET_SIZE
    )
    assert recommended.selection_source == "auto_recommendation"
    assert recommended.auto_diagnostic_digest == state.auto_diagnostic.content_digest
    # The automatic recommendation received no collection authority: the
    # sibling the operator chose by hand is untouched.
    assert state.provisional_entries[0].n_provisional == 4
    assert state.provisional_entries[0].selection_source == "manual"

    # auto -> manual override of the same N. The diagnostic evidence is
    # retained untouched; only that entry's provenance says the choice is now
    # the operator's, and the entry keeps its position.
    diagnostic = state.auto_diagnostic
    assert _select(config, str(fx.SELECTED_TARGET_SIZE)) == 0
    state = _revision(config).state
    assert [entry.n_provisional for entry in state.provisional_entries] == [4, 8]
    manual = state.provisional_entries[1]
    assert manual.selection_source == "manual"
    assert manual.auto_diagnostic_digest is None
    assert state.auto_diagnostic == diagnostic
    # Same N, same substrate: choosing it by hand is the same membership.
    assert manual.membership_digest == diagnostic.recommended_membership_digest

    # An automatic recommendation for a size that is *not* yet in the design
    # appends it like any other size.
    assert _select(config, "--reset") == 0
    assert _sizes(config) == []
    assert _select(config, "2") == 0
    assert _select(config, "--auto") == 0
    assert _sizes(config) == [2, fx.SELECTED_TARGET_SIZE]


# --- 19.4 warm auto ---------------------------------------------------------


def test_a_second_auto_reuses_cached_evidence_and_runs_no_new_work(
    tmp_path: Path, capsys
):
    config, _workspace = _prepared(tmp_path)
    screen = fx._SelectedSizeScreenHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )
    first = _revision(config).state.auto_diagnostic
    capsys.readouterr()

    # Override manually, then ask for the recommendation again. A poison
    # trainer/evaluator proves no TRAIN2 or EVAL2 call is reachable.
    assert _select(config, "4") == 0
    assert _select(config, "--auto") == 0
    output = capsys.readouterr().out
    assert "no screening jobs were rerun" in output

    state = _revision(config).state
    assert state.auto_diagnostic == first
    assert state.provisional_entries[0].n_provisional == fx.SELECTED_TARGET_SIZE
    assert state.provisional_entries[0].selection_source == "auto_recommendation"


# --- 19.7 horizons ----------------------------------------------------------


def test_horizons_resolve_once_and_do_not_drift_with_later_config_edits(
    tmp_path: Path,
):
    config, _workspace = _prepared(tmp_path)
    cfg, _paths = cli._load_config(config)
    defaults = resolve_provisional_horizons(cfg)

    # No flags: both roles resolve from their existing configuration owners.
    assert _select(config, "8") == 0
    proposal = _only(config)
    assert proposal.cv_max_num_epochs == defaults.cv_max_num_epochs
    assert proposal.production_max_num_epochs == defaults.production_max_num_epochs

    # One-sided override touches exactly one role.
    assert _select(config, "8", "--horizon-cv", "17") == 0
    proposal = _only(config)
    assert proposal.cv_max_num_epochs == 17
    assert proposal.production_max_num_epochs == defaults.production_max_num_epochs

    assert _select(config, "8", "--horizon", "23") == 0
    proposal = _only(config)
    # An earlier CLI override is not a sticky default for a later proposal.
    assert proposal.cv_max_num_epochs == defaults.cv_max_num_epochs
    assert proposal.production_max_num_epochs == 23

    # Both flags together.
    assert _select(config, "8", "--horizon-cv", "5", "--horizon", "9") == 0
    proposal = _only(config)
    assert (proposal.cv_max_num_epochs, proposal.production_max_num_epochs) == (5, 9)

    # A later configuration edit does not rewrite the existing proposal.
    before = config.read_text(encoding="utf-8")
    fx.rewrite_config(
        config,
        f"max_num_epochs = {fx.PRODUCTION_MAX_NUM_EPOCHS}",
        f"max_num_epochs = {fx.PRODUCTION_MAX_NUM_EPOCHS + 4}",
    )
    assert config.read_text(encoding="utf-8") != before
    proposal = _only(config)
    assert (proposal.cv_max_num_epochs, proposal.production_max_num_epochs) == (5, 9)

    # ...but the next proposal-setting invocation resolves from current config.
    assert _select(config, "8") == 0
    proposal = _only(config)
    assert proposal.production_max_num_epochs == fx.PRODUCTION_MAX_NUM_EPOCHS + 4


def test_horizons_do_not_participate_in_automatic_diagnostic_identity(
    tmp_path: Path, capsys
):
    config, _workspace = _prepared(tmp_path)
    screen = fx._SelectedSizeScreenHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )
    before = _revision(config).state.auto_diagnostic
    capsys.readouterr()

    # Steering both horizons, then asking for the recommendation again, must not
    # invalidate the screen: a poison trainer proves no rung is rerun.
    assert _select(config, "8", "--horizon-cv", "13", "--horizon", "19") == 0
    assert _select(config, "--auto", "--horizon-cv", "13") == 0
    assert "no screening jobs were rerun" in capsys.readouterr().out
    assert _revision(config).state.auto_diagnostic == before


# --- 19.9 identity hierarchy -----------------------------------------------


def test_role_horizons_are_independent_and_provenance_is_not_identity(
    tmp_path: Path,
):
    from mdstats.training_data.post_selection_identity import (
        resolve_cv_validation_policy_identity,
        resolve_final_production_policy_identity,
    )

    config, _workspace = _prepared(tmp_path)
    cfg, _paths = cli._load_config(config)

    cv_a = resolve_cv_validation_policy_identity(cfg, max_num_epochs=10)
    cv_b = resolve_cv_validation_policy_identity(cfg, max_num_epochs=11)
    prod_a = resolve_final_production_policy_identity(cfg, max_num_epochs=10)
    prod_b = resolve_final_production_policy_identity(cfg, max_num_epochs=11)

    assert cv_a.content_digest != cv_b.content_digest
    assert prod_a.content_digest != prod_b.content_digest
    # Changing the CV horizon cannot move the production identity, and vice versa.
    assert (
        resolve_final_production_policy_identity(cfg, max_num_epochs=10).content_digest
        == prod_a.content_digest
    )
    assert (
        resolve_cv_validation_policy_identity(cfg, max_num_epochs=10).content_digest
        == cv_a.content_digest
    )

    # Same N and same horizons, different provenance -> same target binding.
    assert _select(config, "8", "--horizon-cv", "4", "--horizon", "6") == 0
    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        manual_binding = load_current_selected_training_context(
            cfg, paths, store, admit=True
        ).binding
    finally:
        store.close()
    payload = manual_binding.to_dict()
    for forbidden in ("selection_source", "auto_diagnostic_digest"):
        assert forbidden not in payload


# --- 19.6 / 19.11 the diagnostic never blocks the operator ------------------


def test_a_diagnostic_without_a_recommendation_changes_no_proposal_field(
    tmp_path: Path, capsys
):
    """A real reducer no-recommendation outcome is not a campaign failure."""

    from mdstats.training_data.target_size_experiment import ReducerStatus

    config, _workspace = _prepared(tmp_path)
    assert _select(config, "8", "--horizon-cv", "12") == 0
    before = _only(config)
    capsys.readouterr()

    # A harness whose first boundary fails numerically for every candidate
    # drives the real P2 reducer to INSUFFICIENT_COMPARISON.
    class _NonComparableHarness(fx._SelectedSizeScreenHarness):
        def evaluate(self, *args, **kwargs):
            import numpy as np
            from types import SimpleNamespace

            return [
                SimpleNamespace(
                    energy_ev=float("nan"),
                    forces_ev_per_angstrom=np.full_like(
                        np.asarray(record.forces_ev_per_angstrom, dtype=float),
                        float("nan"),
                    ),
                    stress_ev_per_angstrom3=record.stress_ev_per_angstrom3,
                )
                for record in super().evaluate(*args, **kwargs)
            ]

    harness = _NonComparableHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    ), "a completed diagnostic without a recommendation is a successful result"

    output = capsys.readouterr().out
    assert "without a recommendation" in output
    assert "left unchanged" in output

    state = _revision(config).state
    assert state.lifecycle is TargetSizeLifecycle.DIAGNOSTIC_COMPLETE
    assert state.auto_diagnostic is not None
    assert not state.auto_diagnostic.has_recommendation
    assert state.auto_diagnostic.reducer_status == (
        ReducerStatus.INSUFFICIENT_COMPARISON.value
    )
    # Not one proposal field moved.
    assert _only(config) == before

    # And a qualified candidate can still be added and the design frozen.
    assert _select(config, "4") == 0
    assert _sizes(config) == [8, 4]
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        design = resolve_frozen_target_design(cfg, paths, store, admit=True)
        assert list(design.selected_sizes) == [8, 4]
    finally:
        store.close()


# --- 19.12 the report is a faithful projection ------------------------------


def test_the_portable_report_equals_the_authenticated_evidence(tmp_path: Path):
    from mdstats.training_data.campaign_target_size_report import (
        SCIENTIFIC_LIMITATION,
        auto_diagnostic_report_path,
    )
    from mdstats.training_data.campaign_target_size_view import (
        expose_current_target_size_auto_diagnostic,
    )
    from mdstats.training_data.target_size_experiment import TargetSizeBoundaryMetric

    config, _workspace = _prepared(tmp_path)
    screen = fx._SelectedSizeScreenHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        validated = expose_current_target_size_auto_diagnostic(cfg, paths, store)
    finally:
        store.close()

    report = auto_diagnostic_report_path(paths, validated.revision.state.generation)
    assert report.is_file()
    text = report.read_text(encoding="utf-8")

    assert SCIENTIFIC_LIMITATION in text
    assert "Frozen: no" in text
    assert f"N = {validated.recommended_target_size}" in text
    assert validated.head.content_digest in text
    assert validated.projection.recommended_membership_digest in text

    definition = validated.authorities.aggregate.definition
    for size in definition.qualified_candidate_sizes:
        assert f"| {size} |" in text
    for epoch in definition.policy.fidelity_epochs:
        assert str(epoch) in text

    # Every per-seed RMSE the reducer committed appears verbatim, at the report's
    # own precision, together with its exact arithmetic paired mean.
    history = tuple(validated.head.post_state.outcome_history)
    assert history
    by_cell: dict[tuple[int, int], list[float]] = {}
    for item in history:
        assert isinstance(item, TargetSizeBoundaryMetric)
        assert f"{item.target_force_rmse_mev_per_a:.4f}" in text
        by_cell.setdefault(
            (int(item.boundary_epoch), int(item.target_size)), []
        ).append(float(item.target_force_rmse_mev_per_a))
    for values in by_cell.values():
        assert f"{sum(values) / len(values):.4f}" in text

    # The report is derived: deleting it changes no campaign state, and it is
    # rebuilt on the next exposure.
    report.unlink()
    assert _revision(config).state.auto_diagnostic == validated.projection
    assert _select(config, "--auto") == 0
    assert report.is_file()


# --- 19.10 concurrency ------------------------------------------------------


def test_a_stale_recommendation_never_overwrites_a_newer_decision(
    tmp_path: Path, capsys
):
    """The long-running diagnostic loses to a newer explicit human choice.

    The race is made deterministic by installing the newer proposal through the
    real CampaignStore owner from inside the last boundary's evaluator, i.e.
    while the diagnostic is genuinely mid-flight.
    """

    config, _workspace = _prepared(tmp_path)
    assert _select(config, "4") == 0

    cfg, paths = cli._load_config(config)
    state = {"switched": False}

    class _RacingHarness(fx._SelectedSizeScreenHarness):
        def evaluate(self, *args, **kwargs):
            records = super().evaluate(*args, **kwargs)
            if not state["switched"]:
                state["switched"] = True
                # A concurrent operator decision, through the production owner.
                store = CampaignStore(paths.state_db)
                try:
                    from mdstats.training_data.campaign_target_size_runtime import (
                        load_prepared_target_size_generation,
                    )
                    from mdstats.training_data.campaign_target_size_selection import (
                        build_target_size_proposal,
                        commit_target_size_proposal,
                    )
                    from mdstats.training_data.campaign_target_size_state import (
                        SELECTION_SOURCE_MANUAL,
                    )

                    definition = load_prepared_target_size_generation(
                        cfg,
                        paths,
                        store,
                        load_target_size_campaign_revision(store),
                    ).aggregate.definition
                    commit_target_size_proposal(
                        store,
                        load_target_size_campaign_revision(store),
                        build_target_size_proposal(
                            definition,
                            target_size=2,
                            selection_source=SELECTION_SOURCE_MANUAL,
                            horizons=resolve_provisional_horizons(cfg),
                        ),
                    )
                finally:
                    store.close()
            return records

    harness = _RacingHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    assert state["switched"]
    output = capsys.readouterr().out
    assert "not installed" in output

    current = _revision(config).state
    # The newer human decision stands untouched: the stale recommendation did
    # not append itself, replace an entry, or reorder the design. The evidence
    # and its report are still committed and reusable.
    assert [entry.n_provisional for entry in current.provisional_entries] == [4, 2]
    assert all(
        entry.selection_source == "manual" for entry in current.provisional_entries
    )
    assert current.auto_diagnostic is not None

    # Rerunning warm `--auto` against the current revision installs it with no
    # retraining at all, through the same unique-by-N merge owner.
    assert _select(config, "--auto") == 0
    installed = _revision(config).state
    assert [entry.n_provisional for entry in installed.provisional_entries] == [
        4,
        2,
        fx.SELECTED_TARGET_SIZE,
    ]
    assert installed.provisional_entries[2].selection_source == "auto_recommendation"


def test_a_manual_update_and_a_freeze_serialize_at_the_campaign_boundary(
    tmp_path: Path,
):
    """Exactly one ordering becomes current; the loser sees a real conflict."""

    from mdstats.training_data.campaign_target_size_runtime import (
        load_prepared_target_size_generation,
    )
    from mdstats.training_data.campaign_target_size_selection import (
        build_target_size_proposal,
        commit_target_size_proposal,
    )
    from mdstats.training_data.campaign_target_size_state import (
        SELECTION_SOURCE_MANUAL,
        TargetSizeCampaignConflictError,
    )

    config, _workspace = _prepared(tmp_path)
    assert _select(config, "8") == 0

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        # One writer reads the current revision...
        stale = load_target_size_campaign_revision(store)
        definition = load_prepared_target_size_generation(
            cfg, paths, store, stale
        ).aggregate.definition
        # ...the freeze commits first...
        admitted = resolve_frozen_target_selection(cfg, paths, store, admit=True)
        assert admitted.frozen.n_selected == 8
        # ...and the stale proposal writer loses its compare-and-set outright.
        with pytest.raises(TargetSizeCampaignConflictError):
            commit_target_size_proposal(
                store,
                stale,
                build_target_size_proposal(
                    definition,
                    target_size=4,
                    selection_source=SELECTION_SOURCE_MANUAL,
                    horizons=resolve_provisional_horizons(cfg),
                ),
            )
        current = load_target_size_campaign_revision(store).state
        assert current.frozen_entries is not None and current.provisional_entries == ()
    finally:
        store.close()


# --- 19.11 legacy cutover ---------------------------------------------------


def test_a_pre_rework_terminal_row_is_diagnostic_evidence_and_not_a_freeze():
    """An old `TERMINAL_SELECTED` row loads, and authorizes exactly nothing.

    The persisted chain is append-only, so an existing campaign must still be
    able to read its own head. What it must never do is have that head silently
    mean "the operator approved this size".
    """

    from mdstats.training_data._common import digest
    from mdstats.training_data.campaign_target_size_state import (
        TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA,
        TargetSizeAutoDiagnostic,
        TargetSizeCampaignState,
        TargetSizeRegime,
    )

    def d(name: str) -> str:
        return digest({"fixture": name})

    legacy_payload = {
        "schema": TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA,
        "regime": "current",
        "generation": 3,
        "attempt": "attempt-1",
        "lifecycle": "terminal_selected",
        "frame_authority_digest": d("frame"),
        "neutral_statistical_base_digest": d("neutral"),
        "split_exclusion_digest": d("split"),
        "policy_digest": d("policy"),
        "experiment_definition_digest": d("definition"),
        "aggregate_digest": d("aggregate"),
        "prepared_manifest_digest": d("prepared"),
        "execution_context_digest": d("context"),
        "common_preparation_digest": d("common"),
        "screen_window_digest": d("window"),
        "execution_root": "target-size/g3",
        "adopted_execution_head_digest": d("head"),
        "adopted_reducer_state_digest": d("reducer"),
        "terminal": TargetSizeAutoDiagnostic(
            reducer_status="selected",
            experiment_definition_digest=d("definition"),
            reducer_state_digest=d("reducer"),
            execution_head_digest=d("head"),
            training_order_digest=d("order"),
            recommended_target_size=8,
            recommended_membership_digest=d("membership"),
        ).to_dict(),
        "disposition": "terminal_selection",
        "disposition_detail": None,
    }

    restored = TargetSizeCampaignState.from_dict(legacy_payload)
    assert restored.is_legacy_schema
    assert restored.regime is TargetSizeRegime.CURRENT
    # Read for exactly what it always was: a completed automatic diagnostic.
    assert restored.lifecycle is TargetSizeLifecycle.DIAGNOSTIC_COMPLETE
    assert restored.auto_diagnostic.recommended_target_size == 8
    # And nothing more. It cannot be a frozen operator-approved selection.
    assert restored.provisional_entries == () and restored.frozen_entries is None

    # It still authenticates byte-for-byte, so an existing campaign can read its
    # own head and advance from it.
    assert restored.to_dict()["lifecycle"] == "terminal_selected"
    assert restored.to_dict()["schema"] == TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA
    assert "proposal" not in restored.to_dict()

    # A current-schema successor is what a transition must publish.
    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeCasExpectation,
        TargetSizeTransitionKind,
        _validate_transition_semantics,
    )

    with pytest.raises(TrainingDataInputError, match="current campaign-state schema"):
        _validate_transition_semantics(
            kind=TargetSizeTransitionKind.SET_PROPOSAL,
            expected=TargetSizeCasExpectation(
                regime=TargetSizeRegime.CURRENT,
                generation=3,
                attempt="attempt-1",
                state_revision=d("revision"),
                schema_version=TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA,
            ),
            successor=restored,
        )


def test_a_pre_rework_post_selection_binding_stays_historical():
    """Old descendants are not re-parented onto a new freeze that shares N."""

    from mdstats.training_data._common import digest
    from mdstats.training_data.campaign_post_selection import (
        POST_SELECTION_BINDING_SCHEMA,
        POST_SELECTION_BINDING_V1_SCHEMA,
        PostSelectionBinding,
    )

    def d(name: str) -> str:
        return digest({"fixture": name})

    retired = {
        "schema": POST_SELECTION_BINDING_V1_SCHEMA,
        "campaign_generation": 1,
        "campaign_state_revision": d("revision"),
        "experiment_definition_digest": d("definition"),
        "training_order_digest": d("order"),
        "frame_authority_digest": d("frame"),
        "neutral_statistical_base_digest": d("neutral"),
        "split_exclusion_digest": d("split"),
        "target_size_policy_digest": d("policy"),
        "aggregate_digest": d("aggregate"),
        "adopted_execution_head_digest": d("head"),
        "adopted_reducer_state_digest": d("reducer"),
        "n_selected": 8,
        "selected_membership_digest": d("membership"),
    }
    legacy = PostSelectionBinding.from_dict(retired)
    assert legacy.is_v1_legacy_schema
    assert legacy.is_legacy_schema
    assert legacy.to_dict()["schema"] == POST_SELECTION_BINDING_V1_SCHEMA

    # A fresh current binding that shares N does not match the legacy binding,
    # so old descendants are not re-parented onto a new freeze that shares N.
    current = PostSelectionBinding(
        campaign_generation=1,
        experiment_definition_digest=d("definition"),
        training_order_digest=d("order"),
        frame_authority_digest=d("frame"),
        neutral_statistical_base_digest=d("neutral"),
        split_exclusion_digest=d("split"),
        target_size_policy_digest=d("policy"),
        aggregate_digest=d("aggregate"),
        n_selected=8,
        selected_membership_digest=d("membership"),
    )
    assert current.to_dict()["schema"] == POST_SELECTION_BINDING_SCHEMA
    assert not current.is_legacy_schema
    assert legacy.content_digest != current.content_digest


# --- 19.13 structural closure ----------------------------------------------


def test_no_current_surface_retains_the_retired_selection_semantics():
    """Structural: the retired authority paths are gone, not aliased."""

    retired_symbols = {
        "TargetSizeTerminalProjection",
        "ValidatedTargetSizeTerminalResult",
        "commit_terminal_projection",
        "derive_terminal_projection",
        "validate_terminal_projection",
        "load_validated_target_size_terminal_result",
        "expose_current_target_size_terminal_result",
    }
    offenders: list[str] = []
    for path in sorted(_TRAINING_DATA.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for symbol in retired_symbols:
            if symbol in text:
                offenders.append(f"{path.name}:{symbol}")
        # The retired lifecycle values survive only as the pre-rework wire
        # constants inside the state module's own compatibility reader.
        if path.name != "campaign_target_size_state.py":
            for token in ("TERMINAL_SELECTED", "TERMINAL_SCIENTIFIC_FAILURE"):
                if token in text:
                    offenders.append(f"{path.name}:{token}")
    assert not offenders, offenders

    # P5 never reaches the automatic diagnostic's head/reducer for its ancestry.
    from mdstats.training_data.campaign_post_selection import PostSelectionBinding
    import mdstats.training_data.campaign_post_selection as post_sel_mod

    fields = set(PostSelectionBinding.__dataclass_fields__)
    assert "adopted_execution_head_digest" not in fields
    assert "adopted_reducer_state_digest" not in fields

    legacy_classes = [
        name for name in dir(post_sel_mod) if name.startswith("_Legacy")
    ]
    assert not legacy_classes, f"Synthetic legacy classes remain: {legacy_classes}"

    # And `advance` cannot dispatch the target-size decision.
    source = (_TRAINING_DATA / "_campaign_cli_core.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    advance = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "command_advance"
    )
    called = {
        node.func.id
        for node in ast.walk(advance)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "command_select_target_size" not in called
