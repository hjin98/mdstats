"""P4-A acceptance: canonical target-size campaign state, one generation
authority, transactional predecessor CAS, and deterministic logical-transition
identity.

Every persistence assertion runs against a real ``CampaignStore`` SQLite file,
including close/reopen and two independent connections/processes.  No
in-memory or faked store participates in these claims.
"""

from __future__ import annotations

import ast
import json
import multiprocessing
import sqlite3
from pathlib import Path

import pytest

from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.campaign_target_size_state import (
    TARGET_SIZE_CAMPAIGN_STATE_SCHEMA,
    TargetSizeCampaignConflictError,
    TargetSizeCampaignCorruptionError,
    TargetSizeCampaignState,
    TargetSizeCasExpectation,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTerminalProjection,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
    ensure_target_size_campaign_revision,
    load_target_size_campaign_history,
    load_target_size_campaign_revision,
    target_size_transition_identity,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"


def _d(seed: str) -> str:
    return digest({"fixture": seed})


@pytest.fixture()
def store(tmp_path: Path) -> CampaignStore:
    created = CampaignStore(tmp_path / "state" / "campaign.sqlite3")
    yield created
    created.close()


def _bound_state(
    *,
    generation: int,
    regime: TargetSizeRegime = TargetSizeRegime.TRANSITIONING,
    lifecycle: TargetSizeLifecycle = TargetSizeLifecycle.AUTHORITIES_BOUND,
    attempt: str | None = None,
    aggregate: str = "aggregate",
    **overrides,
) -> TargetSizeCampaignState:
    payload = dict(
        regime=regime,
        generation=generation,
        lifecycle=lifecycle,
        attempt=attempt,
        frame_authority_digest=_d("frame-authority"),
        neutral_statistical_base_digest=_d("neutral-base"),
        split_exclusion_digest=_d("split-exclusion"),
        policy_digest=_d("policy"),
        experiment_definition_digest=_d("definition"),
        aggregate_digest=_d(aggregate),
    )
    payload.update(overrides)
    return TargetSizeCampaignState(**payload)


def _advance(store: CampaignStore, revision, successor, *, kind=TargetSizeTransitionKind.BIND_AUTHORITIES):
    return commit_target_size_campaign_transition(
        store, kind=kind, expected=revision.expectation(), successor=successor
    )


# --- REQ1 schema/serialization roundtrip -----------------------------------


def test_p4a_req1_state_serialization_roundtrip_is_exact():
    terminal = TargetSizeTerminalProjection(
        reducer_status="selected",
        experiment_definition_digest=_d("definition"),
        reducer_state_digest=_d("reducer"),
        execution_head_digest=_d("head"),
        training_order_digest=_d("training-order"),
        selected_target_size=48,
        selected_membership_digest=_d("membership"),
        terminal_reason_codes=("practical_equivalence",),
    )
    state = _bound_state(
        generation=3,
        regime=TargetSizeRegime.CURRENT,
        lifecycle=TargetSizeLifecycle.TERMINAL_SELECTED,
        attempt="attempt-1",
        execution_context_digest=_d("context"),
        common_preparation_digest=_d("common"),
        screen_window_digest=_d("window"),
        execution_root="target-size/screen-3",
        adopted_execution_head_digest=_d("head"),
        adopted_reducer_state_digest=_d("reducer"),
        terminal=terminal,
    )
    encoded = json.dumps(state.to_dict(), sort_keys=True)
    restored = TargetSizeCampaignState.from_dict(json.loads(encoded))
    assert restored == state
    assert restored.content_digest == state.content_digest
    assert restored.terminal == terminal


def test_p4a_req1_tampered_payload_fails_authentication():
    state = _bound_state(generation=1)
    payload = state.to_dict()
    payload["generation"] = 2
    with pytest.raises(TrainingDataSerializationError):
        TargetSizeCampaignState.from_dict(payload)


# --- REQ2 real SQLite close/reopen ------------------------------------------


def test_p4a_req2_state_survives_real_close_and_reopen(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    first = CampaignStore(path)
    genesis = ensure_target_size_campaign_revision(first)
    committed = _advance(
        first,
        genesis,
        _bound_state(generation=1, regime=TargetSizeRegime.TRANSITIONING,
                     lifecycle=TargetSizeLifecycle.AWAITING_AUTHORITIES,
                     frame_authority_digest=None,
                     neutral_statistical_base_digest=None,
                     split_exclusion_digest=None,
                     policy_digest=None,
                     experiment_definition_digest=None,
                     aggregate_digest=None),
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
    ).revision
    first.close()

    reopened = CampaignStore(path)
    try:
        loaded = load_target_size_campaign_revision(reopened)
        assert loaded == committed
        assert loaded.state.generation == 1
        assert loaded.state.regime is TargetSizeRegime.TRANSITIONING
        history = load_target_size_campaign_history(reopened)
        assert [item.sequence for item in history] == [0, 1]
    finally:
        reopened.close()


def test_p4a_req2_genesis_is_created_once_and_reused(store: CampaignStore):
    first = ensure_target_size_campaign_revision(store)
    second = ensure_target_size_campaign_revision(store)
    assert first == second
    assert first.sequence == 0
    assert first.state.regime is TargetSizeRegime.LEGACY
    assert first.state.lifecycle is TargetSizeLifecycle.UNCONVERTED
    assert len(load_target_size_campaign_history(store)) == 1


# --- REQ3 rollback leaves the predecessor unchanged -------------------------


def test_p4a_req3_transaction_rollback_cannot_expose_partial_state(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    boom = RuntimeError("interrupted mid-transition")
    with pytest.raises(RuntimeError):
        with store.exclusive_transaction() as db:
            db.execute(
                "INSERT INTO target_size_campaign_state"
                "(state_revision, sequence, predecessor_revision, transition_identity,"
                " transition_kind, payload, committed_utc) VALUES (?,?,?,?,?,?,?)",
                (
                    _d("rolled-back"),
                    1,
                    genesis.state_revision,
                    _d("rolled-back-identity"),
                    "bind_authorities",
                    json.dumps(_bound_state(generation=0, regime=TargetSizeRegime.CURRENT).to_dict()),
                    "1970-01-01T00:00:00+00:00",
                ),
            )
            raise boom
    assert load_target_size_campaign_revision(store) == genesis
    assert len(load_target_size_campaign_history(store)) == 1


def test_p4a_req3_nested_transactions_are_refused(store: CampaignStore):
    ensure_target_size_campaign_revision(store)
    with store.exclusive_transaction():
        with pytest.raises(Exception) as excinfo:
            with store.exclusive_transaction():
                pass
    assert "must not nest" in str(excinfo.value)


# --- REQ4 older-generation rejection ----------------------------------------


def test_p4a_req4_older_generation_writer_loses_after_takeover(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    generation_one = _advance(
        store,
        genesis,
        _bound_state(generation=1),
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
    ).revision
    stale_expectation = generation_one.expectation()

    generation_two = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.ADVANCE_GENERATION,
        expected=stale_expectation,
        successor=_bound_state(generation=2, aggregate="aggregate-2"),
    ).revision
    assert generation_two.state.generation == 2

    with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.BIND_AUTHORITIES,
            expected=stale_expectation,
            successor=_bound_state(generation=1, aggregate="stale-write"),
        )
    assert excinfo.value.conflict_kind == "stale_generation"
    assert load_target_size_campaign_revision(store) == generation_two


def test_p4a_req4_generation_replacement_clears_subordinate_attempt(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    active = _advance(
        store,
        genesis,
        _bound_state(generation=1, attempt="attempt-a"),
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
    ).revision
    with pytest.raises(TrainingDataInputError):
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.ADVANCE_GENERATION,
            expected=active.expectation(),
            successor=_bound_state(generation=2, attempt="attempt-a"),
        )


def test_p4a_req4_only_generation_transitions_may_change_the_generation(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    active = _advance(
        store,
        genesis,
        _bound_state(generation=1),
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
    ).revision
    with pytest.raises(TrainingDataInputError):
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
            expected=active.expectation(),
            successor=_bound_state(generation=7, attempt="attempt-a"),
        )


# --- REQ5 same-generation stale-revision rejection --------------------------


def test_p4a_req5_same_generation_stale_revision_cannot_mutate(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    first = _advance(
        store, genesis, _bound_state(generation=1), kind=TargetSizeTransitionKind.BEGIN_CUTOVER
    ).revision
    stale = first.expectation()
    second = _advance(
        store, first, _bound_state(generation=1, attempt="attempt-a"),
        kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
    ).revision

    with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
            expected=stale,
            successor=_bound_state(generation=1, attempt="attempt-b"),
        )
    assert excinfo.value.conflict_kind == "stale_revision"
    assert load_target_size_campaign_revision(store) == second


def test_p4a_req5_attempt_mismatch_is_typed_conflict(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    first = _advance(
        store, genesis, _bound_state(generation=1, attempt="attempt-a"),
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
    ).revision
    forged = TargetSizeCasExpectation(
        regime=first.state.regime,
        generation=first.state.generation,
        attempt="attempt-b",
        state_revision=first.state_revision,
    )
    with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.CLOSE_ATTEMPT,
            expected=forged,
            successor=_bound_state(generation=1),
        )
    assert excinfo.value.conflict_kind == "attempt_mismatch"


def test_p4a_req5_regime_mismatch_is_typed_conflict(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    forged = TargetSizeCasExpectation(
        regime=TargetSizeRegime.CURRENT,
        generation=genesis.state.generation,
        attempt=None,
        state_revision=genesis.state_revision,
    )
    with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.BIND_AUTHORITIES,
            expected=forged,
            successor=_bound_state(generation=0),
        )
    assert excinfo.value.conflict_kind == "regime_mismatch"


# --- REQ6 divergent same-predecessor race admits exactly one successor ------


def test_p4a_req6_two_connections_racing_one_predecessor_admit_one_successor(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    writer_a = CampaignStore(path)
    writer_b = CampaignStore(path)
    try:
        genesis = ensure_target_size_campaign_revision(writer_a)
        seen_by_b = load_target_size_campaign_revision(writer_b)
        assert seen_by_b == genesis

        winner = commit_target_size_campaign_transition(
            writer_a,
            kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
            expected=genesis.expectation(),
            successor=_bound_state(generation=1, aggregate="from-a"),
        ).revision
        with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
            commit_target_size_campaign_transition(
                writer_b,
                kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
                expected=seen_by_b.expectation(),
                successor=_bound_state(generation=1, aggregate="from-b"),
            )
        assert excinfo.value.conflict_kind == "stale_generation"
        assert load_target_size_campaign_revision(writer_b) == winner
        assert load_target_size_campaign_revision(writer_a).state.aggregate_digest == _d("from-a")
    finally:
        writer_a.close()
        writer_b.close()


def _race_child(path_text: str, marker: str, queue, barrier) -> None:
    child = CampaignStore(Path(path_text))
    try:
        revision = ensure_target_size_campaign_revision(child)
        # Every child must observe the same predecessor before any child
        # commits; otherwise the processes would serialize instead of racing.
        barrier.wait(timeout=120)
        try:
            commit_target_size_campaign_transition(
                child,
                kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
                expected=revision.expectation(),
                successor=_bound_state(generation=1, aggregate=marker),
            )
        except TargetSizeCampaignConflictError as exc:
            queue.put(("conflict", exc.conflict_kind, marker))
        else:
            queue.put(("committed", None, marker))
    finally:
        child.close()


def test_p4a_req6_process_level_race_admits_exactly_one_successor(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    owner = CampaignStore(path)
    ensure_target_size_campaign_revision(owner)
    owner.close()

    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    barrier = context.Barrier(4)
    children = [
        context.Process(
            target=_race_child, args=(str(path), f"racer-{index}", queue, barrier)
        )
        for index in range(4)
    ]
    for child in children:
        child.start()
    for child in children:
        child.join(timeout=180)
        assert child.exitcode == 0

    outcomes = [queue.get(timeout=30) for _ in children]
    committed = [item for item in outcomes if item[0] == "committed"]
    conflicts = [item for item in outcomes if item[0] == "conflict"]
    assert len(committed) == 1, outcomes
    assert len(conflicts) == 3, outcomes
    assert {item[1] for item in conflicts} == {"stale_generation"}

    verifier = CampaignStore(path)
    try:
        history = load_target_size_campaign_history(verifier)
        assert [item.sequence for item in history] == [0, 1]
        assert history[1].state.aggregate_digest == _d(committed[0][2])
    finally:
        verifier.close()


# --- REQ7 exact logical duplicate retry is idempotent -----------------------


def test_p4a_req7_exact_duplicate_retry_returns_the_committed_successor(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    successor = _bound_state(generation=1)
    first = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis.expectation(),
        successor=successor,
    )
    assert first.idempotent is False

    retry = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis.expectation(),
        successor=successor,
    )
    assert retry.idempotent is True
    assert retry.revision == first.revision
    assert len(load_target_size_campaign_history(store)) == 2


def test_p4a_req7_duplicate_retry_after_further_transitions_still_verifies(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    successor = _bound_state(generation=1)
    first = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis.expectation(),
        successor=successor,
    ).revision
    _advance(
        store, first, _bound_state(generation=1, attempt="attempt-a"),
        kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
    )
    retry = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis.expectation(),
        successor=successor,
    )
    assert retry.idempotent is True
    assert retry.revision == first


def test_p4a_req7_duplicate_genesis_retry_is_idempotent(store: CampaignStore):
    from mdstats.training_data.campaign_target_size_state import (
        initial_target_size_campaign_state,
    )

    first = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.INITIALIZE,
        expected=None,
        successor=initial_target_size_campaign_state(),
    )
    retry = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.INITIALIZE,
        expected=None,
        successor=initial_target_size_campaign_state(),
    )
    assert retry.idempotent is True
    assert retry.revision == first.revision


# --- REQ8 near-duplicate with one changed reference is a conflict -----------


@pytest.mark.parametrize(
    "changed",
    [
        {"aggregate_digest": _d("other-aggregate")},
        {"experiment_definition_digest": _d("other-definition")},
        {"frame_authority_digest": _d("other-frame-authority")},
        {"split_exclusion_digest": _d("other-split-exclusion")},
        {"policy_digest": _d("other-policy")},
    ],
)
def test_p4a_req8_near_duplicate_changed_reference_conflicts(store: CampaignStore, changed):
    """A retry that changed one authoritative reference is a same-generation
    conflict, never an idempotent duplicate."""

    genesis = ensure_target_size_campaign_revision(store)
    cutover = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis.expectation(),
        successor=_bound_state(generation=1),
    ).revision

    successor = _bound_state(generation=1, attempt="attempt-a")
    commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
        expected=cutover.expectation(),
        successor=successor,
    )
    from dataclasses import replace as dataclass_replace

    near_duplicate = dataclass_replace(successor, **changed)
    assert near_duplicate != successor
    with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
            expected=cutover.expectation(),
            successor=near_duplicate,
        )
    assert excinfo.value.conflict_kind == "stale_revision"
    assert len(load_target_size_campaign_history(store)) == 3


def test_p4a_req8_same_successor_under_a_different_kind_is_not_a_duplicate(store: CampaignStore):
    genesis = ensure_target_size_campaign_revision(store)
    successor = _bound_state(generation=1)
    commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis.expectation(),
        successor=successor,
    )
    with pytest.raises(TargetSizeCampaignConflictError):
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.ADVANCE_GENERATION,
            expected=genesis.expectation(),
            successor=successor,
        )


def test_p4a_req8_transition_identity_binds_kind_predecessor_and_successor():
    genesis_expectation = TargetSizeCasExpectation(
        regime=TargetSizeRegime.LEGACY,
        generation=0,
        attempt=None,
        state_revision=_d("predecessor"),
    )
    successor = _bound_state(generation=1)
    base = target_size_transition_identity(
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis_expectation,
        successor=successor,
    )
    assert base == target_size_transition_identity(
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis_expectation,
        successor=successor,
    )
    from dataclasses import replace as dataclass_replace

    assert base != target_size_transition_identity(
        kind=TargetSizeTransitionKind.ADVANCE_GENERATION,
        expected=genesis_expectation,
        successor=successor,
    )
    assert base != target_size_transition_identity(
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=dataclass_replace(genesis_expectation, state_revision=_d("other")),
        successor=successor,
    )
    assert base != target_size_transition_identity(
        kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        expected=genesis_expectation,
        successor=dataclass_replace(successor, aggregate_digest=_d("other-aggregate")),
    )


# --- REQ9 exactly one canonical generation authority ------------------------


def test_p4a_req9_state_table_structurally_admits_one_successor_per_predecessor(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    owner = CampaignStore(path)
    try:
        genesis = ensure_target_size_campaign_revision(owner)
        _advance(
            owner, genesis, _bound_state(generation=1),
            kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
        )
        raw = sqlite3.connect(path)
        try:
            with pytest.raises(sqlite3.IntegrityError):
                raw.execute(
                    "INSERT INTO target_size_campaign_state"
                    "(state_revision, sequence, predecessor_revision, transition_identity,"
                    " transition_kind, payload, committed_utc) VALUES (?,?,?,?,?,?,?)",
                    (
                        _d("forked"),
                        2,
                        genesis.state_revision,
                        _d("forked-identity"),
                        "begin_cutover",
                        "{}",
                        "1970-01-01T00:00:00+00:00",
                    ),
                )
                raw.commit()
        finally:
            raw.close()
    finally:
        owner.close()


def test_p4a_req9_only_one_canonical_generation_symbol_exists_in_current_state_authority():
    """No second independently advancing target-size generation counter."""

    module = _TRAINING_DATA / "campaign_target_size_state.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    state_class = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "TargetSizeCampaignState"
    )
    fields = [
        node.target.id
        for node in state_class.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ]
    generation_fields = [name for name in fields if "generation" in name]
    assert generation_fields == ["generation"], generation_fields
    assert "attempt" in fields


def test_p4a_req9_campaign_store_owns_exactly_one_target_size_state_table(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    owner = CampaignStore(path)
    try:
        raw = sqlite3.connect(path)
        try:
            names = {
                row[0]
                for row in raw.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            raw.close()
    finally:
        owner.close()
    target_size_tables = sorted(
        name for name in names if "target_size" in name
    )
    assert target_size_tables == ["target_size_campaign_state"], sorted(names)


# --- REQ10 retired schema cannot deserialize/relabel as current -------------


def test_p4a_req10_retired_schema_is_never_reinterpreted_as_current():
    retired = {
        "schema": "mdstats.mlff-campaign-prepare-restart.target-size-v5.v4",
        "regime": "current",
        "generation": 9,
        "lifecycle": "authorities_bound",
    }
    with pytest.raises(TrainingDataSerializationError):
        TargetSizeCampaignState.from_dict(retired)


def test_p4a_req10_relabeled_retired_payload_fails_authentication():
    retired = {
        "schema": TARGET_SIZE_CAMPAIGN_STATE_SCHEMA,
        "regime": "current",
        "generation": 9,
        "lifecycle": "authorities_bound",
        "selected_target_size": 64,
        "content_digest": _d("forged"),
    }
    with pytest.raises((TrainingDataSerializationError, TrainingDataInputError, KeyError)):
        TargetSizeCampaignState.from_dict(retired)


def test_p4a_req10_out_of_band_row_edit_is_detected_as_corruption(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    owner = CampaignStore(path)
    try:
        genesis = ensure_target_size_campaign_revision(owner)
        forged = _bound_state(generation=0, regime=TargetSizeRegime.LEGACY,
                              lifecycle=TargetSizeLifecycle.UNCONVERTED,
                              frame_authority_digest=None,
                              neutral_statistical_base_digest=None,
                              split_exclusion_digest=None,
                              policy_digest=None,
                              experiment_definition_digest=None,
                              aggregate_digest=None)
        assert forged == genesis.state
        raw = sqlite3.connect(path)
        try:
            tampered = dict(genesis.state.to_dict())
            tampered["regime"] = "current"
            tampered.pop("content_digest", None)
            state = TargetSizeCampaignState.from_dict(
                {**tampered, "lifecycle": "awaiting_authorities"}
            )
            raw.execute(
                "UPDATE target_size_campaign_state SET payload=? WHERE sequence=0",
                (json.dumps(state.to_dict(), sort_keys=True),),
            )
            raw.commit()
        finally:
            raw.close()
    finally:
        owner.close()

    reopened = CampaignStore(path)
    try:
        with pytest.raises(TargetSizeCampaignCorruptionError):
            load_target_size_campaign_revision(reopened)
    finally:
        reopened.close()


# --- REQ11 version-agnostic production naming -------------------------------


def test_p4a_req11_no_version_prefixed_production_names_in_new_state_authority():
    text = (_TRAINING_DATA / "campaign_target_size_state.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "v7_" not in lowered
    assert "_v7" not in lowered
    tree = ast.parse(text)
    for node in ast.walk(tree):
        name = getattr(node, "name", None) or getattr(node, "id", None)
        if isinstance(name, str):
            assert "v7" not in name.lower(), name


# --- Invariant guards -------------------------------------------------------


def test_p4a_terminal_projection_must_bind_n_and_exact_membership_together():
    with pytest.raises(TrainingDataInputError):
        TargetSizeTerminalProjection(
            reducer_status="selected",
            experiment_definition_digest=_d("definition"),
            reducer_state_digest=_d("reducer"),
            execution_head_digest=_d("head"),
            training_order_digest=_d("training-order"),
            selected_target_size=48,
        )


def test_p4a_terminal_projection_must_match_adopted_references():
    terminal = TargetSizeTerminalProjection(
        reducer_status="selected",
        experiment_definition_digest=_d("definition"),
        reducer_state_digest=_d("reducer"),
        execution_head_digest=_d("head"),
        training_order_digest=_d("training-order"),
        selected_target_size=48,
        selected_membership_digest=_d("membership"),
    )
    with pytest.raises(TrainingDataInputError):
        _bound_state(
            generation=1,
            regime=TargetSizeRegime.CURRENT,
            lifecycle=TargetSizeLifecycle.TERMINAL_SELECTED,
            execution_context_digest=_d("context"),
            common_preparation_digest=_d("common"),
            screen_window_digest=_d("window"),
            execution_root="target-size/screen-1",
            adopted_execution_head_digest=_d("different-head"),
            adopted_reducer_state_digest=_d("reducer"),
            terminal=terminal,
        )


def test_p4a_unconverted_state_cannot_bind_current_authority():
    with pytest.raises(TrainingDataInputError):
        TargetSizeCampaignState(
            regime=TargetSizeRegime.LEGACY,
            generation=0,
            lifecycle=TargetSizeLifecycle.UNCONVERTED,
            aggregate_digest=_d("aggregate"),
        )


def test_p4a_execution_root_cannot_escape_the_campaign_workspace():
    for bad in ("/absolute/root", "../escape", "target-size/../../escape"):
        with pytest.raises(TrainingDataInputError):
            _bound_state(
                generation=1,
                regime=TargetSizeRegime.CURRENT,
                lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
                execution_context_digest=_d("context"),
                common_preparation_digest=_d("common"),
                screen_window_digest=_d("window"),
                execution_root=bad,
            )
