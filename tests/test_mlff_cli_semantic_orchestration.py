from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import mdstats
import pytest
from mdstats.training_data import _campaign_cli_core as cli


ACTIVE = (
    mdstats.OUTCOME_AWAITING_COARSE_SCREEN,
    mdstats.OUTCOME_AWAITING_SHORT_SCREEN,
    mdstats.OUTCOME_AWAITING_FINAL_SCREEN,
)

DEFAULT_FIDELITY = (1, 3, 10)
DEFAULT_HORIZON = 30


def _cfg() -> dict:
    return {"training": {"policy_generation": "train2"}}


def _paths() -> SimpleNamespace:
    return SimpleNamespace(state_db=Path("state.sqlite3"))


def _study(outcome: str, *, selected: int | None = None) -> SimpleNamespace:
    boundary = {
        mdstats.OUTCOME_AWAITING_COARSE_SCREEN: (DEFAULT_FIDELITY[0], (512, 1024, 2048, 4096)),
        mdstats.OUTCOME_AWAITING_SHORT_SCREEN: (DEFAULT_FIDELITY[1], (1024, 2048)),
        mdstats.OUTCOME_AWAITING_FINAL_SCREEN: (DEFAULT_FIDELITY[2], (2048,)),
    }.get(outcome, (None, ()))
    return SimpleNamespace(
        outcome=outcome,
        decision_reason="fixture",
        selected_target_size=selected,
        next_training_epoch=boundary[0],
        next_training_sizes=boundary[1],
        qualified_sizes=(512, 1024, 2048, 4096),
        policy=SimpleNamespace(screening_optimizer_seeds=(1, 2)),
        candidate_authority_digest="a" * 64,
        content_digest="b" * 64,
    )


def test_materialize_requires_selected_train2_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths()
    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: object())
    monkeypatch.setattr(
        cli,
        "_load_verified_target_size_study_authority",
        lambda _store: _study(mdstats.OUTCOME_AWAITING_SHORT_SCREEN),
    )
    with pytest.raises(cli.CampaignCliError, match="Run `select-target-size` first"):
        cli.command_materialize(argparse.Namespace(config="campaign.toml", max_new_domains=None))

    historical = {"training": {"policy_generation": "legacy"}}
    monkeypatch.setattr(cli, "_load_config", lambda _path: (historical, paths))
    with pytest.raises(cli.CampaignCliError, match="TRAIN2 lifecycle command"):
        cli.command_materialize(argparse.Namespace(config="campaign.toml", max_new_domains=None))



def test_materialize_idempotent_rerun_does_not_reopen_completed_production_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths()
    store = object()
    selected = _study(mdstats.OUTCOME_SELECTED, selected=2048)
    entries = [SimpleNamespace(variant_id="selected")]
    marks: list[tuple[str, cli.StageState]] = []
    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: store)
    monkeypatch.setattr(cli, "_load_verified_target_size_study_authority", lambda _store: selected)
    monkeypatch.setattr(cli, "_validate_train2_data8_matrix", lambda *_args: (entries, "selected production/CV"))
    monkeypatch.setattr(cli, "_data8_matrix_digest", lambda _entries: "same-matrix")
    monkeypatch.setattr(cli, "_execute_prepare_current_authority", lambda _args: 0)
    monkeypatch.setattr(
        cli, "_mark_stage",
        lambda _store, _paths, name, state, _message: marks.append((name, state)),
    )
    assert cli.command_materialize(argparse.Namespace(config="campaign.toml", max_new_domains=None)) == 0
    assert marks == []


def test_materialize_new_selected_matrix_invalidates_execution_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _paths()
    store = object()
    selected = _study(mdstats.OUTCOME_SELECTED, selected=2048)
    entries = [SimpleNamespace(variant_id="selected")]
    marks: list[tuple[str, cli.StageState]] = []
    calls = {"count": 0}
    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: store)
    monkeypatch.setattr(cli, "_load_verified_target_size_study_authority", lambda _store: selected)

    def validate(*_args):
        calls["count"] += 1
        if calls["count"] == 1:
            raise cli.CampaignCliError("screening matrix still active")
        return entries, "selected production/CV"

    monkeypatch.setattr(cli, "_validate_train2_data8_matrix", validate)
    monkeypatch.setattr(cli, "_data8_matrix_digest", lambda _entries: "selected-matrix")
    monkeypatch.setattr(cli, "_execute_prepare_current_authority", lambda _args: 0)
    monkeypatch.setattr(
        cli, "_mark_stage",
        lambda _store, _paths, name, state, _message: marks.append((name, state)),
    )
    assert cli.command_materialize(argparse.Namespace(config="campaign.toml", max_new_domains=None)) == 0
    assert marks == [
        ("preflight", cli.StageState.WAITING),
        ("train", cli.StageState.WAITING),
        ("evaluate", cli.StageState.WAITING),
    ]

def test_prepare_rejects_post_selection_semantic_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths()
    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: object())
    monkeypatch.setattr(
        cli,
        "_load_train2_study_optional",
        lambda _store: _study(mdstats.OUTCOME_SELECTED, selected=2048),
    )
    with pytest.raises(cli.CampaignCliError, match="run `materialize`"):
        cli.command_prepare(argparse.Namespace(config="campaign.toml"))


@pytest.mark.parametrize(
    ("initial_outcome", "expected_boundaries"),
    [
        (mdstats.OUTCOME_AWAITING_COARSE_SCREEN, list(DEFAULT_FIDELITY)),
        (mdstats.OUTCOME_AWAITING_SHORT_SCREEN, list(DEFAULT_FIDELITY[1:])),
        (mdstats.OUTCOME_AWAITING_FINAL_SCREEN, [DEFAULT_FIDELITY[2]]),
    ],
)
def test_select_target_size_owns_complete_restartable_funnel(
    monkeypatch: pytest.MonkeyPatch,
    initial_outcome: str,
    expected_boundaries: list[int],
) -> None:
    paths = _paths()
    order = list(ACTIVE)
    start = order.index(initial_outcome)
    studies = [_study(value) for value in order[start:]] + [
        _study(mdstats.OUTCOME_SELECTED, selected=2048)
    ]
    holder = {"index": 0}
    train_boundaries: list[int] = []
    eval_boundaries: list[int] = []
    preflight_checks: list[str] = []

    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: object())
    monkeypatch.setattr(
        cli,
        "_load_verified_target_size_study_authority",
        lambda _store: studies[holder["index"]],
    )
    monkeypatch.setattr(
        cli,
        "_require_train2_preflight_authorization",
        lambda _cfg, _paths, _store, study: preflight_checks.append(study.outcome),
    )

    def fake_train(args: argparse.Namespace) -> int:
        study = studies[holder["index"]]
        train_boundaries.append(study.next_training_epoch)
        assert args._target_size_orchestrated is True
        assert args.run_id is None
        assert args.seed is None
        assert args.selection_size is None
        assert args.max_runs is None
        return 0

    def fake_evaluate(args: argparse.Namespace) -> int:
        study = studies[holder["index"]]
        eval_boundaries.append(study.next_training_epoch)
        assert args._target_size_orchestrated is True
        assert args.require_complete is True
        holder["index"] += 1
        return 0

    monkeypatch.setattr(cli, "_execute_train_current_authority", fake_train)
    monkeypatch.setattr(cli, "_execute_evaluate_current_authority", fake_evaluate)

    assert cli.command_select_target_size(argparse.Namespace(config="campaign.toml")) == 0
    assert train_boundaries == expected_boundaries
    assert eval_boundaries == expected_boundaries
    # Initial validation plus one validation at each still-active boundary.
    assert preflight_checks[0] == initial_outcome
    assert len(preflight_checks) == len(expected_boundaries) + 1



@pytest.mark.parametrize("command_name", ["command_train", "command_evaluate"])
def test_selected_production_commands_require_current_matrix_preflight(
    monkeypatch: pytest.MonkeyPatch, command_name: str
) -> None:
    paths = _paths()
    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: object())
    monkeypatch.setattr(
        cli,
        "_load_verified_target_size_study_authority",
        lambda _store: _study(mdstats.OUTCOME_SELECTED, selected=2048),
    )
    monkeypatch.setattr(
        cli,
        "_require_train2_preflight_authorization",
        lambda *_args: (_ for _ in ()).throw(cli.CampaignCliError("stale matrix")),
    )
    with pytest.raises(cli.CampaignCliError, match="selected-size production/CV DATA8 matrix"):
        getattr(cli, command_name)(argparse.Namespace(config="campaign.toml"))

def test_select_target_size_selected_is_idempotent(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    paths = _paths()
    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: object())
    monkeypatch.setattr(
        cli,
        "_load_verified_target_size_study_authority",
        lambda _store: _study(mdstats.OUTCOME_SELECTED, selected=4096),
    )
    monkeypatch.setattr(
        cli,
        "_execute_train_current_authority",
        lambda _args: pytest.fail("selected study must not retrain"),
    )
    monkeypatch.setattr(
        cli,
        "_execute_evaluate_current_authority",
        lambda _args: pytest.fail("selected study must not re-evaluate"),
    )
    assert cli.command_select_target_size(argparse.Namespace(config="campaign.toml")) == 0
    assert "already selected and frozen: n=4096" in capsys.readouterr().out


def test_scientific_terminal_target_size_has_no_production_next_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = _study(mdstats.OUTCOME_NONCONVERGED_AT_FIXED_CEILING)
    monkeypatch.setattr(cli, "_load_train2_study_optional", lambda _store: terminal)
    monkeypatch.setattr(cli, "_effective_stage", lambda *_args: (cli.StageState.COMPLETE, "receipt"))
    lifecycle = cli._train2_public_lifecycle(_cfg(), _paths(), SimpleNamespace(
        stage=lambda _name: (cli.StageState.COMPLETE, "receipt"),
        has_record=lambda key: key == "preflight_smoke",
        get_payload=lambda _key: {"passed": True},
    ))
    stop = next(step for step in lifecycle if step.semantic_id == "target_size_selection")
    assert stop.terminal is True
    assert cli._next_public_operation(_cfg(), _paths(), SimpleNamespace(
        stage=lambda _name: (cli.StageState.COMPLETE, "receipt"),
        has_record=lambda key: key == "preflight_smoke",
        get_payload=lambda _key: {"passed": True},
    )) is None


def test_screening_preflight_remains_bound_across_halving_when_matrix_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    method = SimpleNamespace(mode="multihead_replay", fold_partition_seed=17)
    monkeypatch.setattr(cli, "_training_method_specs", lambda _cfg: (method,))
    shapes = {
        ("multihead_replay", size, seed, 0)
        for size in (512, 1024, 2048, 4096)
        for seed in (1, 2)
    }
    entries = [
        SimpleNamespace(
            variant_id=f"v-{index}",
            shape=shape,
            materialization=SimpleNamespace(
                checkpoint=SimpleNamespace(
                    plan=SimpleNamespace(
                        selection_authority_role="target_size_candidate",
                        target_size_study_digest="a" * 64,
                    )
                )
            ),
        )
        for index, shape in enumerate(sorted(shapes))
    ]
    monkeypatch.setattr(cli, "_current_data8_entries", lambda _store: entries)
    monkeypatch.setattr(cli, "_data8_entry_variant_shape", lambda entry: entry.shape)
    monkeypatch.setattr(cli, "_data8_matrix_digest", lambda _entries: "matrix-digest")

    store = SimpleNamespace(
        has_record=lambda key: key == "preflight_smoke",
        get_payload=lambda _key: {"passed": True, "data8_matrix_digest": "matrix-digest"},
    )
    monkeypatch.setattr(cli, "_effective_stage", lambda *_args: (cli.StageState.COMPLETE, "passed"))

    for outcome in ACTIVE:
        study = _study(outcome)
        got_entries, phase = cli._require_train2_preflight_authorization(_cfg(), _paths(), store, study)
        assert got_entries == entries
        assert phase == "target-size screening"


def test_preflight_fails_closed_when_current_matrix_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    entries = [SimpleNamespace(variant_id="candidate")]
    monkeypatch.setattr(
        cli,
        "_validate_train2_data8_matrix",
        lambda _cfg, _store, _study: (entries, "target-size screening"),
    )
    monkeypatch.setattr(cli, "_data8_matrix_digest", lambda _entries: "new-matrix")
    monkeypatch.setattr(cli, "_effective_stage", lambda *_args: (cli.StageState.COMPLETE, "passed"))
    store = SimpleNamespace(
        has_record=lambda key: key == "preflight_smoke",
        get_payload=lambda _key: {"passed": True, "data8_matrix_digest": "old-matrix"},
    )
    with pytest.raises(cli.CampaignCliError, match="changed after preflight"):
        cli._require_train2_preflight_authorization(
            _cfg(), _paths(), store, _study(mdstats.OUTCOME_AWAITING_SHORT_SCREEN)
        )


def test_advance_uses_same_derived_next_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _paths()
    monkeypatch.setattr(cli, "_load_config", lambda _path: (_cfg(), paths))
    store = object()
    monkeypatch.setattr(cli, "CampaignStore", lambda _path: store)
    monkeypatch.setattr(cli, "_next_public_operation", lambda _cfg, _paths, got: "select-target-size")
    called: list[str] = []
    monkeypatch.setattr(
        cli,
        "command_select_target_size",
        lambda args: called.append(args.config) or 0,
    )
    assert cli.command_advance(argparse.Namespace(config="campaign.toml")) == 0
    assert called == ["campaign.toml"]


@pytest.mark.parametrize(
    ("outcome", "matrix_ok", "preflight_ok", "train_state", "eval_state", "verify_state", "expected"),
    [
        (mdstats.OUTCOME_AWAITING_COARSE_SCREEN, True, False, cli.StageState.NOT_STARTED, cli.StageState.NOT_STARTED, cli.StageState.NOT_STARTED, "preflight"),
        (mdstats.OUTCOME_AWAITING_SHORT_SCREEN, True, True, cli.StageState.WAITING, cli.StageState.WAITING, cli.StageState.NOT_STARTED, "select-target-size"),
        (mdstats.OUTCOME_SELECTED, False, False, cli.StageState.WAITING, cli.StageState.WAITING, cli.StageState.NOT_STARTED, "materialize"),
        (mdstats.OUTCOME_SELECTED, True, False, cli.StageState.WAITING, cli.StageState.WAITING, cli.StageState.NOT_STARTED, "preflight"),
        (mdstats.OUTCOME_SELECTED, True, True, cli.StageState.WAITING, cli.StageState.WAITING, cli.StageState.NOT_STARTED, "train"),
        (mdstats.OUTCOME_SELECTED, True, True, cli.StageState.COMPLETE, cli.StageState.WAITING, cli.StageState.NOT_STARTED, "evaluate"),
        (mdstats.OUTCOME_SELECTED, True, True, cli.StageState.COMPLETE, cli.StageState.COMPLETE, cli.StageState.WAITING, "verify"),
        (mdstats.OUTCOME_SELECTED, True, True, cli.StageState.COMPLETE, cli.StageState.COMPLETE, cli.StageState.COMPLETE, None),
    ],
)
def test_derived_train2_lifecycle_resolves_one_semantic_next_operation(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    matrix_ok: bool,
    preflight_ok: bool,
    train_state: cli.StageState,
    eval_state: cli.StageState,
    verify_state: cli.StageState,
    expected: str | None,
) -> None:
    study = _study(outcome, selected=2048 if outcome == mdstats.OUTCOME_SELECTED else None)
    states = {
        "doctor": cli.StageState.COMPLETE,
        "prepare": cli.StageState.COMPLETE,
        "preflight": cli.StageState.COMPLETE if preflight_ok else cli.StageState.WAITING,
        "train": train_state,
        "evaluate": eval_state,
        "verify": verify_state,
    }

    class Store:
        def stage(self, name):
            return states.get(name, cli.StageState.NOT_STARTED), "fixture"

    monkeypatch.setattr(cli, "_load_train2_study_optional", lambda _store: study)
    monkeypatch.setattr(
        cli,
        "_effective_stage",
        lambda _store, _paths, name: (states.get(name, cli.StageState.NOT_STARTED), "fixture"),
    )

    def validate(*_args):
        if not matrix_ok:
            raise cli.CampaignCliError("matrix is stale")
        return [], "selected production/CV" if outcome == mdstats.OUTCOME_SELECTED else "target-size screening"

    def authorize(*_args):
        if not preflight_ok:
            raise cli.CampaignCliError("preflight is stale")
        return [], "selected production/CV" if outcome == mdstats.OUTCOME_SELECTED else "target-size screening"

    monkeypatch.setattr(cli, "_validate_train2_data8_matrix", validate)
    monkeypatch.setattr(cli, "_require_train2_preflight_authorization", authorize)
    assert cli._next_public_operation(_cfg(), _paths(), Store()) == expected
