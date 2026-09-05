"""`qualification status` is one coherent, authenticated answer.

The public campaign status projection was repaired to read the target-size
revision and every descendant pointer inside one transaction and to authenticate
every compact record it interprets.  `qualification status` had a second, weaker
path beside it: each P7 pointer was read in its own transaction, and the plan,
component evidence, locked activation and release pointer were interpreted out
of bytes that merely parsed.  Only the terminal record went through its typed
store.

That mattered because an operator acts on this answer.  "locked activation:
not activated" is a claim about irreversible disclosure; a component status is
what decides whether qualification is rerun; a release pointer is a release
claim.  None of them may come from durable bytes that do not reproduce the
identity the owner published, and none of them may be assembled from pointer
reads taken at different moments.

These tests drive the real public command and the real P7 stores and
publishers.  The corruption matrix proves the answer degrades to a typed
blocked/unreadable condition without mutating anything; the coherence matrix
proves one real publication transaction cannot land inside one answer.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import tests._mlff_observation_race as race
import tests._mlff_post_selection_fixture as p5
import tests._mlff_qualification_fixture as fx
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_lifecycle import campaign_owner_snapshot
from mdstats.training_data.qualification.errors import QualificationLineageError
from mdstats.training_data.qualification.observation import (
    ABSENT,
    PRESENT,
    UNREADABLE,
    UNREADABLE_EVIDENCE,
    UNREADABLE_POSITION,
    observe_current_qualification,
)
from mdstats.training_data.qualification.runtime import read_component_position
from mdstats.training_data.qualification.spec import (
    resolve_qualification_spec_identity,
)
from mdstats.training_data.qualification.store import (
    POINTER_LOCKED_ACTIVATION,
    POINTER_QUALIFICATION_PLAN,
    POINTER_QUALIFICATION_RECORD,
    POINTER_RELEASE_EVIDENCE,
    publish_current_qualification_pointer,
    qualification_root,
)


# ---------------------------------------------------------------------------
# one release-qualified campaign, reused by the whole matrix
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    """A real campaign driven to `release_qualified`, locked cohort opened.

    Every P7 pointer this command can interpret -- plan, terminal record,
    locked activation and release index -- is published by its real owner, so
    the matrix below tampers with objects that were genuinely produced.
    """

    tmp_path = tmp_path_factory.mktemp("qualification-status")
    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        fx.supply_analytic_reference_bundle(session, harness)
    finally:
        store.close()
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    assert (
        fx.run_qualification_command(
            config, "activate-locked", harness=harness, confirm=True
        )
        == 0
    )
    _cfg, paths = cli._load_config(config)
    return config, paths, harness


def _observe(config: Path, paths):
    """Exactly what the public command computes, through the same owners."""

    cfg, _paths = cli._load_config(config, ensure=False)
    with cli.observational_campaign_state():
        store = CampaignStore(paths.state_db, create=False)
        try:
            _revision, binding, pointers = campaign_owner_snapshot(store)
            if binding is None:
                return None
            return observe_current_qualification(
                paths,
                binding,
                pointers,
                specification_digest=resolve_qualification_spec_identity(
                    cfg
                ).content_digest,
            )
        finally:
            store.close()


def _binding(paths):
    store = CampaignStore(paths.state_db, create=False)
    try:
        return campaign_owner_snapshot(store)[1]
    finally:
        store.close()


def _root(paths):
    store = CampaignStore(paths.state_db, create=False)
    try:
        revision, _snapshot_binding, _pointers = campaign_owner_snapshot(store)
    finally:
        store.close()
    return qualification_root(paths, revision.state.generation)


def _pointer(paths, kind: str) -> str:
    binding = _binding(paths)
    store = CampaignStore(paths.state_db, create=False)
    try:
        _revision, _snapshot_binding, pointers = campaign_owner_snapshot(store)
    finally:
        store.close()
    value = pointers.get(f"qualification:{binding.content_digest}:{kind}")
    assert value is not None, f"the fixture published no {kind} pointer"
    return str(value)


def _object_path(root: Path, digest: str) -> Path:
    return root / "objects" / digest[:2] / f"{digest}.json"


def _managed_snapshot(paths) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(paths.workspace.rglob("*")):
        key = str(path.relative_to(paths.workspace))
        if path.is_dir():
            snapshot[key] = "<dir>"
        elif path.is_file():
            snapshot[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            snapshot[key] = "<other>"
    return snapshot


def _database_rows(paths) -> dict[str, list[tuple]]:
    db = sqlite3.connect(f"file:{paths.state_db}?mode=ro", uri=True)
    try:
        return {
            table: sorted(db.execute(f"SELECT * FROM {table}").fetchall(), key=repr)
            for table in ("meta", "records", "stages", "target_size_campaign_state")
        }
    finally:
        db.close()


def _corruptions(original: bytes) -> dict[str, bytes | None]:
    """Three ways an object stops being what the pointer named."""

    payload = json.loads(original.decode("utf-8"))
    misidentified = dict(payload)
    # Still a parseable object of the same shape; one recorded value differs, so
    # it no longer reproduces the digest the pointer names.
    misidentified["schema"] = str(misidentified.get("schema", "")) + "-tampered"
    return {
        "missing": None,
        "malformed": b"{ this is not json",
        "misidentified": json.dumps(misidentified, sort_keys=True).encode("utf-8"),
    }


def _attempt_root(config: Path, paths, root: Path) -> Path:
    """The attempt directory the owner really used, named by its own plan."""

    identity = _observe(config, paths).attempt_identity
    assert identity is not None
    return root / "attempts" / identity


def _component_evidence_path(config: Path, paths, root: Path, component: str):
    position = read_component_position(_attempt_root(config, paths, root), component)
    assert position is not None
    return _object_path(root, str(position["evidence_digest"]))


# ---------------------------------------------------------------------------
# integrity: a pointer is a claim about content, not a fact about it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target", ["plan", "component", "locked", "release", "record"]
)
@pytest.mark.parametrize("corruption", ["missing", "malformed", "misidentified"])
def test_tampered_p7_evidence_is_never_reported_as_current_truth(
    qualified, target: str, corruption: str, capsys
):
    config, paths, _harness = qualified
    root = _root(paths)

    healthy = _observe(config, paths)
    assert healthy is not None
    assert healthy.blocked_detail is None
    assert healthy.verdict == "release_qualified"
    assert healthy.locked_state == PRESENT
    assert healthy.release_state == PRESENT
    assert healthy.planned_components

    component = None
    if target == "component":
        component = healthy.planned_components[0]
        path = _component_evidence_path(config, paths, root, component)
        healthy_status = dict(healthy.component_states)[component]
    else:
        kind = {
            "plan": POINTER_QUALIFICATION_PLAN,
            "locked": POINTER_LOCKED_ACTIVATION,
            "release": POINTER_RELEASE_EVIDENCE,
            "record": POINTER_QUALIFICATION_RECORD,
        }[target]
        path = _object_path(root, _pointer(paths, kind))
    assert path.is_file()
    original = path.read_bytes()

    try:
        payload = _corruptions(original)[corruption]
        if payload is None:
            path.unlink()
        else:
            path.write_bytes(payload)
        # Snapshot the tampered workspace: what is under test is that observing
        # it changes nothing, including that it never repairs or recreates the
        # object it could not authenticate.
        before_files = _managed_snapshot(paths)
        before_rows = _database_rows(paths)

        observation = _observe(config, paths)
        assert observation is not None
        assert observation.blocked_detail is not None

        if target == "plan":
            # With no authentic plan there is no authentic component list, so
            # no component state is asserted either.
            assert observation.planned_components == ()
            assert observation.component_states == ()
        elif target == "component":
            assert dict(observation.component_states)[component] == (
                UNREADABLE_EVIDENCE
            )
            assert healthy_status != UNREADABLE_EVIDENCE
        elif target == "locked":
            assert observation.locked_state == UNREADABLE
            assert observation.locked_activated_at is None
            # Never "not activated": that would deny an irreversible disclosure.
            assert observation.locked_state != ABSENT
        elif target == "release":
            assert observation.release_state == UNREADABLE
            assert observation.release_evidence_digest is None
        else:
            assert observation.verdict is None
            assert observation.verdict_reason is None

        # The real public command stays non-mutating and truthful.
        capsys.readouterr()
        assert cli.main(["--config", str(config), "qualification", "status"]) == 0
        out = capsys.readouterr().out
        assert "incomplete or corrupt" in out
        if target == "record":
            assert "release_qualified" not in out
        if target == "locked":
            assert "not activated" not in out
        assert _managed_snapshot(paths) == before_files
        assert _database_rows(paths) == before_rows
    finally:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original)

    restored = _observe(config, paths)
    assert restored.blocked_detail is None
    assert restored.verdict == "release_qualified"


def _locator_mutations(locator: dict) -> dict[str, dict]:
    """Ways a current-schema locator stops satisfying its own contract.

    Each one still parses, and each one still leaves an authentic immutable
    position object and authentic evidence on disk.  What is under test is that
    coordination bytes which no longer satisfy the accepted representation are
    not allowed to choose which authentic evidence an operator is shown.
    """

    other_digest = hashlib.sha256(b"a different subject").hexdigest()

    def without(*fields: str) -> dict:
        return {key: value for key, value in locator.items() if key not in fields}

    def replacing(field: str, value) -> dict:
        mutated = dict(locator)
        mutated[field] = value
        return mutated

    return {
        # The bypass this amendment exists for: deleting only the mandatory
        # object reference used to read as the historical direct representation.
        "no_position_object": without("position_object"),
        "no_position_object_or_digest": without(
            "position_object", "position_object_digest"
        ),
        "no_position_object_digest": without("position_object_digest"),
        "no_evidence_digest": without("evidence_digest"),
        "no_component_input_digest": without("component_input_digest"),
        "empty_position_object": replacing("position_object", ""),
        "mistyped_position_object": replacing("position_object", 17),
        "tampered_position_object_digest": replacing(
            "position_object_digest", hashlib.sha256(b"tampered").hexdigest()
        ),
        # Declared claims that the authenticated object it names contradicts.
        "disagreeing_component": replacing("component", "not_this_component"),
        "disagreeing_binding": replacing("binding_digest", other_digest),
        "disagreeing_input": replacing("component_input_digest", other_digest),
        "disagreeing_evidence": replacing("evidence_digest", other_digest),
        # Representation discrimination: neither a current locator nor the exact
        # historical direct shape.
        "no_schema": without("schema"),
        "unknown_schema": replacing("schema", "mdstats.something-else.v1"),
        "legacy_schema_on_locator": replacing("schema", None),
        "near_miss_legacy": {
            "component": locator["component"],
            "binding_digest": locator["binding_digest"],
            "component_input_digest": locator["component_input_digest"],
            "evidence_digest": locator["evidence_digest"],
        },
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "no_position_object",
        "no_position_object_or_digest",
        "no_position_object_digest",
        "no_evidence_digest",
        "no_component_input_digest",
        "empty_position_object",
        "mistyped_position_object",
        "tampered_position_object_digest",
        "disagreeing_component",
        "disagreeing_binding",
        "disagreeing_input",
        "disagreeing_evidence",
        "no_schema",
        "unknown_schema",
        "legacy_schema_on_locator",
        "near_miss_legacy",
    ],
)
def test_a_position_that_does_not_satisfy_its_representation_is_unreadable(
    qualified, mutation: str, capsys
):
    """Mutable position bytes degrade to a diagnostic, not to semantic truth."""

    config, paths, _harness = qualified
    root = _root(paths)
    attempt = _attempt_root(config, paths, root)

    healthy = _observe(config, paths)
    component = healthy.planned_components[0]
    healthy_status = dict(healthy.component_states)[component]
    assert healthy_status != UNREADABLE_POSITION
    locator_path = attempt / "components" / f"{component}.json"
    original = locator_path.read_bytes()
    locator = json.loads(original.decode("utf-8"))
    assert locator.get("position_object"), "the fixture published no position object"
    assert locator.get("position_object_digest")

    try:
        payload = _locator_mutations(locator)[mutation]
        locator_path.write_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))
        before_files = _managed_snapshot(paths)
        before_rows = _database_rows(paths)

        # The single shared reader is the boundary under test.
        with pytest.raises(QualificationLineageError):
            read_component_position(attempt, component)

        observation = _observe(config, paths)
        assert dict(observation.component_states)[component] == UNREADABLE_POSITION
        assert observation.blocked_detail is not None

        # The real public command stays truthful and non-mutating.
        capsys.readouterr()
        assert cli.main(["--config", str(config), "qualification", "status"]) == 0
        assert "incomplete or corrupt" in capsys.readouterr().out
        assert _managed_snapshot(paths) == before_files
        assert _database_rows(paths) == before_rows
    finally:
        locator_path.write_bytes(original)

    assert dict(_observe(config, paths).component_states)[component] == healthy_status


def test_the_exact_historical_direct_position_still_reads_through_both_owners(
    qualified, capsys
):
    """Compatibility is a validated shape, not "anything without a locator".

    The pre-locator writer published the position payload itself at the locator
    path, carrying no schema tag and no component-input identity.  That exact
    shape must still read -- through the session owner and through the public
    command -- so that tightening the current locator does not silently strand
    an attempt directory written before the locator existed.
    """

    config, paths, _harness = qualified
    root = _root(paths)
    attempt = _attempt_root(config, paths, root)

    healthy = _observe(config, paths)
    component = healthy.planned_components[0]
    healthy_status = dict(healthy.component_states)[component]
    locator_path = attempt / "components" / f"{component}.json"
    original = locator_path.read_bytes()
    locator = json.loads(original.decode("utf-8"))

    legacy = {
        "component": locator["component"],
        "binding_digest": locator["binding_digest"],
        "evidence_digest": locator["evidence_digest"],
    }
    try:
        locator_path.write_bytes(json.dumps(legacy, sort_keys=True).encode("utf-8"))

        assert read_component_position(attempt, component) == legacy

        _cfg, _paths, store, session = fx.load_session(config, _harness)
        try:
            evidence = session.completed_component(component)
            assert evidence is not None
            assert evidence.content_digest == legacy["evidence_digest"]
        finally:
            store.close()

        before_files = _managed_snapshot(paths)
        observation = _observe(config, paths)
        assert dict(observation.component_states)[component] == healthy_status
        assert observation.blocked_detail is None

        capsys.readouterr()
        assert cli.main(["--config", str(config), "qualification", "status"]) == 0
        assert "incomplete or corrupt" not in capsys.readouterr().out
        assert _managed_snapshot(paths) == before_files
    finally:
        locator_path.write_bytes(original)

    assert dict(_observe(config, paths).component_states)[component] == healthy_status


@pytest.mark.parametrize(
    "field", ["component", "binding_digest", "evidence_digest"]
)
def test_a_near_miss_of_the_historical_direct_position_fails_closed(
    qualified, field: str
):
    """The historical shape is validated on its own terms, not merely accepted."""

    config, paths, _harness = qualified
    attempt = _attempt_root(config, paths, _root(paths))

    healthy = _observe(config, paths)
    component = healthy.planned_components[0]
    locator_path = attempt / "components" / f"{component}.json"
    original = locator_path.read_bytes()
    locator = json.loads(original.decode("utf-8"))
    legacy = {
        "component": locator["component"],
        "binding_digest": locator["binding_digest"],
        "evidence_digest": locator["evidence_digest"],
    }
    legacy[field] = ""

    try:
        locator_path.write_bytes(json.dumps(legacy, sort_keys=True).encode("utf-8"))
        with pytest.raises(QualificationLineageError):
            read_component_position(attempt, component)
        observation = _observe(config, paths)
        assert dict(observation.component_states)[component] == UNREADABLE_POSITION
        assert observation.blocked_detail is not None
    finally:
        locator_path.write_bytes(original)


def test_an_absent_attempt_state_is_absence_and_a_corrupt_one_is_blocked(qualified):
    config, paths, _harness = qualified
    state_path = _attempt_root(config, paths, _root(paths)) / "attempt-state.json"
    original = state_path.read_bytes()

    healthy = _observe(config, paths)
    assert healthy.attempt_state is not None

    try:
        state_path.write_bytes(b"{ not json")
        observation = _observe(config, paths)
        assert observation.attempt_state == "unreadable"
        assert observation.blocked_detail is not None
    finally:
        state_path.write_bytes(original)
    assert _observe(config, paths).attempt_state == healthy.attempt_state


# ---------------------------------------------------------------------------
# coherence: one answer is one owner ancestry
# ---------------------------------------------------------------------------


def _projection(observation) -> tuple:
    if observation is None:
        return ("no-binding",)
    return (
        observation.generation,
        observation.binding_digest,
        observation.plan_digest,
        observation.component_states,
        observation.locked_state,
        observation.locked_activated_at,
        observation.release_state,
        observation.verdict,
    )


def _withdraw(paths, key: str) -> None:
    db = sqlite3.connect(paths.state_db)
    try:
        db.execute("DELETE FROM meta WHERE key=?", (key,))
        db.commit()
    finally:
        db.close()


@pytest.mark.parametrize(
    "kind",
    [
        POINTER_QUALIFICATION_PLAN,
        POINTER_QUALIFICATION_RECORD,
        POINTER_LOCKED_ACTIVATION,
        POINTER_RELEASE_EVIDENCE,
    ],
)
def test_a_p7_pointer_publication_cannot_land_inside_one_status_answer(
    qualified, kind: str
):
    """The real publication transaction is serialized against the real answer.

    The observer is paused inside its own open read transaction, between the
    target-size head read and the first pointer read -- the exact window a
    hybrid answer would need.  The real publisher then tries to commit with a
    short busy timeout.  It is excluded, so no pointer this answer interprets
    could have moved underneath it, and the answer is one whole owner graph.
    """

    config, paths, _harness = qualified
    binding = _binding(paths)
    digest = _pointer(paths, kind)
    key = f"qualification:{binding.content_digest}:{kind}"

    after = _projection(_observe(config, paths))
    _withdraw(paths, key)
    before = _projection(_observe(config, paths))
    assert before != after, "the fixture did not make the two graphs differ"

    def publish(store) -> None:
        publish_current_qualification_pointer(
            store, binding=binding, kind=kind, content_digest=digest
        )

    store = CampaignStore(paths.state_db)
    try:
        answer, outcome = race.observe_during_open_publication(
            lambda: _projection(_observe(config, paths)), publish, store
        )
        assert outcome == "excluded"
        assert answer == before
        publish(store)
    finally:
        store.close()

    assert _projection(_observe(config, paths)) == after


def test_a_target_generation_adoption_cannot_land_inside_one_status_answer(
    tmp_path: Path,
):
    """The generation an answer describes is the generation it read from.

    `qualification status` derives its binding from the target-size revision, so
    an adoption that lands between the revision read and the pointer reads would
    describe P7 evidence of one generation under the identity of another.
    """

    from mdstats.training_data.campaign_target_size_cutover import (
        ensure_current_target_size_authorities,
    )

    config, _workspace = p5.build_selected_campaign(
        tmp_path, config_text=fx.fixture_config_text()
    )
    _cfg, paths = cli._load_config(config)

    before = _projection(_observe(config, paths))
    assert before != ("no-binding",)

    store = CampaignStore(paths.state_db, create=False)
    try:
        revision, _snapshot_binding, _pointers = campaign_owner_snapshot(store)
    finally:
        store.close()
    identity = {
        name: getattr(revision.state, name)
        for name in (
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "policy_digest",
            "experiment_definition_digest",
            "aggregate_digest",
        )
    }
    # A changed scientific identity is what really advances the generation.
    identity["policy_digest"] = hashlib.sha256(b"a different policy").hexdigest()

    def adopt(store) -> None:
        ensure_current_target_size_authorities(
            store,
            identity,
            common_preparation_digest=revision.state.common_preparation_digest,
            prepared_manifest_digest=revision.state.prepared_manifest_digest,
        )

    store = CampaignStore(paths.state_db)
    try:
        answer, outcome = race.observe_during_open_publication(
            lambda: _projection(_observe(config, paths)), adopt, store
        )
        assert outcome == "excluded"
        assert answer == before
        adopt(store)
    finally:
        store.close()

    after = _projection(_observe(config, paths))
    assert after != before
