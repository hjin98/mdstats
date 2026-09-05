"""One lifecycle answer is one coherent, authenticated read.

Two properties are tested, and they are independent:

*Coherence.*  The public projection reads the target-size revision and every
P5/P7 pointer row inside one SQLite read transaction.  Re-reading the target
revision afterwards was not enough, because publishing a P5 or P7 pointer
mutates ``meta`` without moving that revision at all: an answer could combine a
pre-publication P5 view with a post-publication P7 view and describe an ancestry
that never existed.

*Integrity.*  A pointer names a content digest.  The compact record it names is
loaded through its accepted read-only typed store, so a record that is missing,
unparseable, or simply does not reproduce the identity the pointer named is
reported as ``BLOCKED`` rather than believed.  Cheap observation may skip
re-authenticating models and sources; it may not read ``accepted`` or a release
verdict out of bytes that merely parse.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path

import pytest

import tests._mlff_qualification_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_lifecycle as lifecycle_module
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_lifecycle import (
    LifecycleObservationState,
    project_campaign_lifecycle,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)
from mdstats.training_data.post_selection_store import (
    POINTER_CV_ACCEPTANCE,
    POINTER_FINAL_PUBLICATION,
    post_selection_root,
    publish_current_post_selection_pointer,
)
from mdstats.training_data.qualification.store import (
    POINTER_QUALIFICATION_RECORD,
    publish_current_qualification_pointer,
    qualification_root,
)

import tests.test_mlff_campaign_prepare_boundary as boundary


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


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


def _project(paths):
    """Project exactly as an observational command does.

    The observational capability is part of what is under test: it is what
    keeps the read-only store read-only and stops nested owners from writing
    process-local caches, so a projection taken outside it would not be the
    thing `status` actually runs.
    """

    with cli.observational_campaign_state():
        store = CampaignStore(paths.state_db, create=False)
        try:
            return project_campaign_lifecycle(paths, store)
        finally:
            store.close()


def _binding(paths):
    store = CampaignStore(paths.state_db, create=False)
    try:
        revision = load_target_size_campaign_revision(store)
    finally:
        store.close()
    return lifecycle_module._binding_for(revision), revision


def _pointer(paths, namespace: str, kind: str) -> str:
    binding, _revision = _binding(paths)
    db = sqlite3.connect(f"file:{paths.state_db}?mode=ro", uri=True)
    try:
        row = db.execute(
            "SELECT value FROM meta WHERE key=?",
            (f"{namespace}:{binding.content_digest}:{kind}",),
        ).fetchone()
    finally:
        db.close()
    assert row is not None, f"the fixture published no {kind} pointer"
    return str(row[0])


def _object_path(root: Path, digest: str) -> Path:
    return root / "objects" / digest[:2] / f"{digest}.json"


def _step_states(snapshot) -> tuple[tuple[str, str], ...]:
    return tuple((step.key, step.state) for step in snapshot.steps)


# ---------------------------------------------------------------------------
# integrity: a pointer is a claim about content, not a fact about it
# ---------------------------------------------------------------------------


def _qualified(tmp_path: Path):
    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        fx.supply_analytic_reference_bundle(session, harness)
    finally:
        store.close()
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _cfg, paths = cli._load_config(config)
    return config, paths, harness


def _corruptions(path: Path) -> dict[str, bytes]:
    """Three ways a referenced object stops being what the pointer named."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    misidentified = dict(payload)
    # Keep it a parseable object of the same shape, but change one recorded
    # value so it no longer reproduces the digest the pointer names.
    misidentified["schema"] = str(misidentified.get("schema", "")) + "-tampered"
    return {
        "missing": b"",
        "malformed": b"{ this is not json",
        "misidentified": json.dumps(misidentified, indent=2, sort_keys=True).encode(
            "utf-8"
        ),
    }


@pytest.mark.parametrize(
    "namespace,kind,step_key",
    [
        ("post_selection", POINTER_CV_ACCEPTANCE, "post_selection_cv"),
        ("post_selection", POINTER_FINAL_PUBLICATION, "final_production"),
        ("qualification", POINTER_QUALIFICATION_RECORD, "post_production_qualification"),
    ],
)
def test_a_referenced_record_that_is_not_what_the_pointer_named_is_blocked(
    tmp_path: Path, namespace: str, kind: str, step_key: str
):
    _config, paths, _harness = _qualified(tmp_path)
    digest = _pointer(paths, namespace, kind)
    binding, revision = _binding(paths)
    root = (
        post_selection_root(paths, revision.state.generation)
        if namespace == "post_selection"
        else qualification_root(paths, revision.state.generation)
    )
    path = _object_path(root, digest)
    assert path.is_file()
    original = path.read_bytes()

    healthy = _project(paths)
    assert healthy.step(step_key).state != LifecycleObservationState.BLOCKED

    for name, payload in _corruptions(path).items():
        if name == "missing":
            path.unlink()
        else:
            path.write_bytes(payload)
        before_files = _managed_snapshot(paths)
        before_rows = _database_rows(paths)

        snapshot = _project(paths)
        assert snapshot.step(step_key).state == LifecycleObservationState.BLOCKED, name

        assert _managed_snapshot(paths) == before_files, name
        assert _database_rows(paths) == before_rows, name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original)

    assert _step_states(_project(paths)) == _step_states(healthy)


# ---------------------------------------------------------------------------
# coherence: an answer is an ancestry that actually existed
# ---------------------------------------------------------------------------


def _race(paths, mutate) -> list[tuple[tuple[str, str], ...]]:
    """Project the lifecycle repeatedly while ``mutate`` commits, once."""

    observations: list[tuple[tuple[str, str], ...]] = []
    stop = threading.Event()

    def observe() -> None:
        while not stop.is_set():
            observations.append(_step_states(_project(paths)))

    watcher = threading.Thread(target=observe)
    watcher.start()
    try:
        mutate()
    finally:
        stop.set()
        watcher.join(timeout=300)
    observations.append(_step_states(_project(paths)))
    return observations


def test_answers_across_a_real_prepare_adoption_are_never_hybrid(tmp_path: Path):
    config, cfg, paths = boundary._prepared(tmp_path)
    before = _step_states(_project(paths))

    def advance() -> None:
        boundary._mutate_one_source(cfg, paths)
        assert p4d._run(config, "prepare") == 0

    observations = _race(paths, advance)
    after = _step_states(_project(paths))
    assert observations, "the observer never ran"
    for observed in observations:
        assert observed in (before, after)


def test_answers_across_p5_and_p7_pointer_publication_are_never_hybrid(
    tmp_path: Path,
):
    """The hybrid this closes: a pre-P5 view combined with a post-P7 view.

    P5 and P7 pointer publication mutates ``meta`` without moving the
    target-size state revision, so re-reading that revision proves nothing.
    The two pointers are withdrawn and then republished through the real
    campaign store while the projection runs; every answer must be one of the
    two owner graphs that actually existed.
    """

    _config, paths, _harness = _qualified(tmp_path)
    binding, _revision = _binding(paths)
    publication_digest = _pointer(
        paths, "post_selection", POINTER_FINAL_PUBLICATION
    )
    record_digest = _pointer(paths, "qualification", POINTER_QUALIFICATION_RECORD)
    keys = (
        f"post_selection:{binding.content_digest}:{POINTER_FINAL_PUBLICATION}",
        f"qualification:{binding.content_digest}:{POINTER_QUALIFICATION_RECORD}",
    )

    after = _step_states(_project(paths))
    db = sqlite3.connect(paths.state_db)
    try:
        db.executemany("DELETE FROM meta WHERE key=?", [(key,) for key in keys])
        db.commit()
    finally:
        db.close()
    before = _step_states(_project(paths))
    assert before != after, "the fixture did not make the two graphs differ"

    store = CampaignStore(paths.state_db)
    try:

        def republish() -> None:
            publish_current_post_selection_pointer(
                store,
                binding=binding,
                kind=POINTER_FINAL_PUBLICATION,
                content_digest=publication_digest,
            )
            publish_current_qualification_pointer(
                store,
                binding=binding,
                kind=POINTER_QUALIFICATION_RECORD,
                content_digest=record_digest,
            )

        observations = _race(paths, republish)
    finally:
        store.close()

    assert observations
    assert _step_states(_project(paths)) == after
    for observed in observations:
        assert observed in (before, after)
