"""P4-B acceptance: durable legacy -> transitioning -> current regime cutover,
canonical-generation allocation under CAS, retired-state quarantine, and
fail-closed guidance for incompatible workspaces.

All persistence assertions run against real ``CampaignStore`` SQLite files,
including fresh processes that never saw the originating in-memory objects.
"""

from __future__ import annotations

import json
import multiprocessing
import sqlite3
from pathlib import Path

import pytest

from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data._common import digest
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeCampaignConflictError,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
    ensure_target_size_campaign_revision,
    load_target_size_campaign_history,
    load_target_size_campaign_revision,
)
from mdstats.training_data.campaign_target_size_cutover import (
    QUARANTINE_KEY_PREFIX,
    RETIRED_TARGET_SIZE_RECORD_KEYS,
    RETIRED_TARGET_SIZE_RECORD_PREFIXES,
    REUSABLE_LOWER_LEVEL_RECORD_KEYS,
    TargetSizeCutoverError,
    assert_no_retired_target_size_authority,
    begin_target_size_cutover,
    bind_current_target_size_authorities,
    complete_target_size_cutover,
    inventory_retired_target_size_state,
    quarantine_retired_target_size_state,
    require_current_target_size_runtime,
)


def _d(seed: str) -> str:
    return digest({"fixture": seed})


_AUTHORITIES = dict(
    frame_authority_digest=_d("frame-authority"),
    neutral_statistical_base_digest=_d("neutral-base"),
    split_exclusion_digest=_d("split-exclusion"),
    policy_digest=_d("policy"),
    experiment_definition_digest=_d("definition"),
    aggregate_digest=_d("aggregate"),
)


@pytest.fixture()
def store(tmp_path: Path) -> CampaignStore:
    created = CampaignStore(tmp_path / "state" / "campaign.sqlite3")
    yield created
    created.close()


def _seed_legacy_workspace(store: CampaignStore) -> None:
    """Populate a workspace with retired target-size authority and reusable inputs."""

    store.put_record(
        "target_size_study",
        {
            "schema": "mdstats.target-size-study.v5",
            "outcome": "selected",
            "selected_target_size": 96,
            "domain_prefix_digests": [["domain-a", _d("domain-a")]],
        },
    )
    store.put_record(
        "target_data_role_freeze", {"schema": "retired", "size_development": [1, 2]}
    )
    store.put_record("target_coverage_feasibility", {"schema": "retired"})
    store.put_record("target_multi_view_repair_v2", {"schema": "retired"})
    store.put_record("target_multi_view_qualification_v2", {"schema": "retired"})
    store.put_record("prepare_restart_receipt", {"schema": "retired"})
    store.put_record("mlcv_campaign_cv", {"schema": "retired"})
    store.put_record("materialization:target-96", {"schema": "retired"})
    store.put_record("data8:target-96", {"schema": "retired"})
    store.put_record("execution:seed-0", {"schema": "retired"})
    store.put_record("evaluation:boundary-1", {"schema": "retired"})
    # Lower-level content-addressed inputs that do not encode target-size semantics.
    store.put_record("source_catalog", {"schema": "data2", "runs": ["run-a"]})
    store.put_record("data5", {"schema": "data5"})
    # Unrelated current state that the cutover must not touch.
    store.put_record("replay_plan", {"schema": "replay"})
    store.put_record("production_qualification", {"schema": "data9a"})


# --- REQ1 a fresh campaign reaches the current regime -----------------------


def test_p4b_req1_fresh_campaign_reaches_current_regime(store: CampaignStore):
    inventory = inventory_retired_target_size_state(store)
    assert inventory.is_empty

    transitioning = begin_target_size_cutover(store)
    assert transitioning.state.regime is TargetSizeRegime.TRANSITIONING
    assert transitioning.state.generation == 1
    assert quarantine_retired_target_size_state(store, generation=1) == ()

    bound = bind_current_target_size_authorities(store, transitioning, **_AUTHORITIES)
    current = complete_target_size_cutover(store, bound)

    assert current.state.regime is TargetSizeRegime.CURRENT
    assert current.state.generation == 1
    assert current.state.lifecycle is TargetSizeLifecycle.AUTHORITIES_BOUND
    assert current.state.aggregate_digest == _AUTHORITIES["aggregate_digest"]
    assert require_current_target_size_runtime(store) == current


def test_p4b_req1_current_campaign_refuses_a_second_cutover(store: CampaignStore):
    transitioning = begin_target_size_cutover(store)
    bound = bind_current_target_size_authorities(store, transitioning, **_AUTHORITIES)
    complete_target_size_cutover(store, bound)
    with pytest.raises(TargetSizeCutoverError) as excinfo:
        begin_target_size_cutover(store)
    assert "cannot be repeated" in str(excinfo.value)


# --- REQ2 a legacy workspace enters the transition exactly once -------------


def test_p4b_req2_legacy_workspace_enters_transition_once(store: CampaignStore):
    _seed_legacy_workspace(store)
    genesis = ensure_target_size_campaign_revision(store)
    assert genesis.state.regime is TargetSizeRegime.LEGACY
    assert genesis.state.generation == 0

    first = begin_target_size_cutover(store)
    assert first.state.regime is TargetSizeRegime.TRANSITIONING
    assert first.state.generation == 1

    # Re-entering returns the persisted transition rather than allocating a
    # second generation.
    again = begin_target_size_cutover(store)
    assert again == first
    assert [item.sequence for item in load_target_size_campaign_history(store)] == [0, 1]


def test_p4b_req2_inventory_separates_retired_authority_from_reusable_inputs(
    store: CampaignStore,
):
    _seed_legacy_workspace(store)
    inventory = inventory_retired_target_size_state(store)

    assert "target_size_study" in inventory.retired_record_keys
    assert "target_data_role_freeze" in inventory.retired_record_keys
    assert "materialization:target-96" in inventory.retired_record_keys
    assert "data8:target-96" in inventory.retired_record_keys
    assert "execution:seed-0" in inventory.retired_record_keys
    assert "mlcv_campaign_cv" in inventory.retired_record_keys

    assert inventory.reusable_lower_level_record_keys == ("source_catalog", "data5")
    assert "source_catalog" not in inventory.retired_record_keys
    assert "replay_plan" not in inventory.retired_record_keys
    assert "production_qualification" not in inventory.retired_record_keys


# --- REQ3 retired records never become current authority --------------------


def test_p4b_req3_retired_records_are_quarantined_not_translated(store: CampaignStore):
    _seed_legacy_workspace(store)
    transitioning = begin_target_size_cutover(store)
    before = set(store.record_keys())

    moved = quarantine_retired_target_size_state(
        store, generation=transitioning.state.generation
    )
    assert "target_size_study" in moved

    after = set(store.record_keys())
    for key in moved:
        assert key not in after
        assert f"{QUARANTINE_KEY_PREFIX}g1:{key}" in after
    # Nothing was deleted outright; retired state stays as forensic history.
    assert len(after) == len(before)
    # Reusable and unrelated records are untouched.
    assert {"source_catalog", "data5", "replay_plan", "production_qualification"} <= after
    assert_no_retired_target_size_authority(store)


def test_p4b_req3_old_selected_n_cannot_be_read_as_current_authority(
    store: CampaignStore,
):
    _seed_legacy_workspace(store)
    transitioning = begin_target_size_cutover(store)
    quarantine_retired_target_size_state(
        store, generation=transitioning.state.generation
    )
    bound = bind_current_target_size_authorities(store, transitioning, **_AUTHORITIES)
    current = complete_target_size_cutover(store, bound)

    assert store.get_payload_optional("target_size_study") is None
    assert current.state.terminal is None
    # The retired selected size exists only under the quarantine namespace.
    quarantined = store.get_payload(f"{QUARANTINE_KEY_PREFIX}g1:target_size_study")
    assert quarantined["selected_target_size"] == 96
    # ...and the current authority never acquired it: no selected size, no
    # terminal projection, and no retired reference of any kind.
    assert current.state.terminal is None
    payload = current.state.to_dict()
    assert 96 not in [value for value in payload.values() if isinstance(value, int)]
    assert set(payload) & {"selected_target_size", "domain_prefix_digests"} == set()


def test_p4b_req3_promotion_is_refused_while_retired_authority_is_reachable(
    store: CampaignStore,
):
    _seed_legacy_workspace(store)
    transitioning = begin_target_size_cutover(store)
    bound = bind_current_target_size_authorities(store, transitioning, **_AUTHORITIES)
    with pytest.raises(TargetSizeCutoverError) as excinfo:
        complete_target_size_cutover(store, bound)
    assert "still reachable as current authority" in str(excinfo.value)
    assert load_target_size_campaign_revision(store).state.regime is (
        TargetSizeRegime.TRANSITIONING
    )


def test_p4b_req3_quarantine_is_idempotent(store: CampaignStore):
    _seed_legacy_workspace(store)
    transitioning = begin_target_size_cutover(store)
    first = quarantine_retired_target_size_state(store, generation=1)
    snapshot = set(store.record_keys())
    second = quarantine_retired_target_size_state(store, generation=1)
    assert first
    assert second == ()
    assert set(store.record_keys()) == snapshot


def test_p4b_req3_retired_key_and_prefix_inventory_covers_the_frozen_list():
    """Section 7.3 retired-state inventory is present in the owner, not implied."""

    for key in (
        "target_size_study",
        "target_data_role_freeze",
        "target_coverage_feasibility",
        "target_coverage_sparse_index",
        "target_multi_view_selection_v2",
        "target_multi_view_repair_v2",
        "target_multi_view_qualification_v2",
        "prepare_restart_receipt",
        "target_size_historical_candidate_authority",
    ):
        assert key in RETIRED_TARGET_SIZE_RECORD_KEYS
    for prefix in ("materialization:", "data8:", "execution:", "evaluation:"):
        assert prefix in RETIRED_TARGET_SIZE_RECORD_PREFIXES
    assert not set(REUSABLE_LOWER_LEVEL_RECORD_KEYS) & set(
        RETIRED_TARGET_SIZE_RECORD_KEYS
    )


# --- REQ4 a crash resumes the exact transition ------------------------------


def _resume_child(path_text: str, queue) -> None:
    child = CampaignStore(Path(path_text))
    try:
        revision = begin_target_size_cutover(child)
        quarantine_retired_target_size_state(
            child, generation=revision.state.generation
        )
        bound = bind_current_target_size_authorities(child, revision, **_AUTHORITIES)
        current = complete_target_size_cutover(child, bound)
        queue.put(
            (
                current.state.regime.value,
                current.state.generation,
                current.sequence,
                current.state.aggregate_digest,
            )
        )
    finally:
        child.close()


def test_p4b_req4_fresh_process_resumes_the_exact_interrupted_transition(
    tmp_path: Path,
):
    path = tmp_path / "state" / "campaign.sqlite3"
    starter = CampaignStore(path)
    _seed_legacy_workspace(starter)
    interrupted = begin_target_size_cutover(starter)
    assert interrupted.state.generation == 1
    starter.close()  # the originating process dies here

    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    child = context.Process(target=_resume_child, args=(str(path), queue))
    child.start()
    child.join(timeout=180)
    assert child.exitcode == 0
    regime, generation, sequence, aggregate = queue.get(timeout=30)

    assert regime == "current"
    # The resumed cutover kept the persisted generation instead of allocating a
    # second one; process identity was irrelevant.
    assert generation == 1
    assert aggregate == _AUTHORITIES["aggregate_digest"]

    verifier = CampaignStore(path)
    try:
        history = load_target_size_campaign_history(verifier)
        assert [item.transition_kind for item in history] == [
            TargetSizeTransitionKind.INITIALIZE,
            TargetSizeTransitionKind.BEGIN_CUTOVER,
            TargetSizeTransitionKind.BIND_AUTHORITIES,
            TargetSizeTransitionKind.COMPLETE_CUTOVER,
        ]
        assert {item.state.generation for item in history} == {0, 1}
        assert_no_retired_target_size_authority(verifier)
    finally:
        verifier.close()


def test_p4b_req4_interrupted_quarantine_replays_on_resume(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    starter = CampaignStore(path)
    _seed_legacy_workspace(starter)
    revision = begin_target_size_cutover(starter)
    # Simulate a crash in the middle of quarantine by moving only one record.
    with starter.exclusive_transaction() as db:
        db.execute(
            "UPDATE records SET key=? WHERE key=?",
            (f"{QUARANTINE_KEY_PREFIX}g1:target_size_study", "target_size_study"),
        )
    starter.close()

    resumed = CampaignStore(path)
    try:
        again = begin_target_size_cutover(resumed)
        assert again.state.generation == revision.state.generation
        moved = quarantine_retired_target_size_state(resumed, generation=1)
        assert "target_size_study" not in moved
        assert "target_data_role_freeze" in moved
        assert_no_retired_target_size_authority(resumed)
    finally:
        resumed.close()


# --- REQ5 a competing transition is rejected --------------------------------


def test_p4b_req5_competing_cutover_transition_is_rejected(tmp_path: Path):
    path = tmp_path / "state" / "campaign.sqlite3"
    writer_a = CampaignStore(path)
    writer_b = CampaignStore(path)
    try:
        _seed_legacy_workspace(writer_a)
        genesis_a = ensure_target_size_campaign_revision(writer_a)
        genesis_b = load_target_size_campaign_revision(writer_b)
        assert genesis_a == genesis_b

        winner = begin_target_size_cutover(writer_a)
        with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
            commit_target_size_campaign_transition(
                writer_b,
                kind=TargetSizeTransitionKind.BEGIN_CUTOVER,
                expected=genesis_b.expectation(),
                successor=winner.state.__class__(
                    regime=TargetSizeRegime.TRANSITIONING,
                    generation=1,
                    lifecycle=TargetSizeLifecycle.AWAITING_AUTHORITIES,
                    disposition="competing_cutover",
                ),
            )
        assert excinfo.value.conflict_kind == "stale_generation"
        assert [
            item.sequence for item in load_target_size_campaign_history(writer_b)
        ] == [0, 1]
    finally:
        writer_a.close()
        writer_b.close()


def test_p4b_req5_repeating_the_exact_completion_is_idempotent_not_a_second_cutover(
    store: CampaignStore,
):
    """An interrupted writer that already committed the promotion may retry it;
    the retry returns the same revision instead of forking the chain."""

    _seed_legacy_workspace(store)
    transitioning = begin_target_size_cutover(store)
    quarantine_retired_target_size_state(store, generation=1)
    bound = bind_current_target_size_authorities(store, transitioning, **_AUTHORITIES)
    first = complete_target_size_cutover(store, bound)
    retry = complete_target_size_cutover(store, bound)
    assert retry == first
    assert [item.sequence for item in load_target_size_campaign_history(store)] == [
        0,
        1,
        2,
        3,
    ]


def test_p4b_req5_divergent_transition_from_a_stale_revision_is_rejected(
    store: CampaignStore,
):
    _seed_legacy_workspace(store)
    transitioning = begin_target_size_cutover(store)
    quarantine_retired_target_size_state(store, generation=1)
    bound = bind_current_target_size_authorities(store, transitioning, **_AUTHORITIES)
    complete_target_size_cutover(store, bound)

    divergent = bound.state.__class__(
        regime=TargetSizeRegime.CURRENT,
        generation=bound.state.generation,
        lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
        frame_authority_digest=_d("other-frame-authority"),
        neutral_statistical_base_digest=_AUTHORITIES["neutral_statistical_base_digest"],
        split_exclusion_digest=_AUTHORITIES["split_exclusion_digest"],
        policy_digest=_AUTHORITIES["policy_digest"],
        experiment_definition_digest=_AUTHORITIES["experiment_definition_digest"],
        aggregate_digest=_AUTHORITIES["aggregate_digest"],
    )
    with pytest.raises(TargetSizeCampaignConflictError) as excinfo:
        commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.COMPLETE_CUTOVER,
            expected=bound.expectation(),
            successor=divergent,
        )
    assert excinfo.value.conflict_kind == "stale_revision"


# --- REQ6 no mixed runtime and actionable fail-closed guidance --------------


def test_p4b_req6_legacy_campaign_fails_closed_with_reset_guidance(
    store: CampaignStore,
):
    _seed_legacy_workspace(store)
    ensure_target_size_campaign_revision(store)
    with pytest.raises(TargetSizeCutoverError) as excinfo:
        require_current_target_size_runtime(store)
    message = str(excinfo.value)
    assert "never migrated or reinterpreted" in message
    assert "`prepare`" in message


def test_p4b_req6_uninitialized_campaign_fails_closed(store: CampaignStore):
    with pytest.raises(TargetSizeCutoverError):
        require_current_target_size_runtime(store)


def test_p4b_req6_transitioning_campaign_fails_closed_with_resume_guidance(
    store: CampaignStore,
):
    _seed_legacy_workspace(store)
    begin_target_size_cutover(store)
    with pytest.raises(TargetSizeCutoverError) as excinfo:
        require_current_target_size_runtime(store)
    message = str(excinfo.value)
    assert "resume the exact interrupted cutover" in message
    assert "no mixed old/new runtime" in message


def test_p4b_req6_regime_is_campaign_wide_not_per_record(tmp_path: Path):
    """The regime lives in one campaign-scoped row, so no dataset can execute a
    retired selection path while another executes P1-P3."""

    path = tmp_path / "state" / "campaign.sqlite3"
    owner = CampaignStore(path)
    try:
        _seed_legacy_workspace(owner)
        transitioning = begin_target_size_cutover(owner)
        quarantine_retired_target_size_state(owner, generation=1)
        bound = bind_current_target_size_authorities(
            owner, transitioning, **_AUTHORITIES
        )
        complete_target_size_cutover(owner, bound)
        raw = sqlite3.connect(path)
        try:
            rows = raw.execute(
                "SELECT COUNT(*) FROM target_size_campaign_state"
            ).fetchone()[0]
            regimes = {
                json.loads(payload)["regime"]
                for (payload,) in raw.execute(
                    "SELECT payload FROM target_size_campaign_state "
                    "ORDER BY sequence DESC LIMIT 1"
                ).fetchall()
            }
        finally:
            raw.close()
        assert rows == 4
        assert regimes == {"current"}
    finally:
        owner.close()


# --- Naming ----------------------------------------------------------------


def test_p4b_no_version_prefixed_production_names():
    module = (
        Path(__file__).resolve().parents[1]
        / "mdstats"
        / "training_data"
        / "campaign_target_size_cutover.py"
    )
    text = module.read_text(encoding="utf-8").lower()
    assert "v7_" not in text
    assert "_v7" not in text
