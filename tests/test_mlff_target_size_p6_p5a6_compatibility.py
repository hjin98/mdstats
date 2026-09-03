"""P6 revision-4 acceptance: a real P5A6-created workspace still reopens.

The fixture under ``qualification/p6-p5a6-compat/workspace`` was produced by the
exact accepted P5A6 baseline (commit ``1670275`` / tree ``17e2c56``) through the
real production CLI, the real ``CampaignStore``/SQLite file, the real P4
reducer/terminal owners, and the real post-selection CV and fresh
final-production owners.  It has been preserved byte-for-byte since, and this
module proves the final P6 candidate opens it **unchanged**: no regeneration, no
pre-load rewrite, no migration, and no reconstructed state in the harness.

This is deliberately distinct from the P6-to-P6 restart claim and from the
retired-generation reject-before-reuse claim; neither may stand in for it.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_post_selection import (
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
    resolve_current_final_production_plan,
)
from mdstats.training_data.campaign_target_size_cutover import (
    require_current_target_size_runtime,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    TargetSizeRegime,
    load_target_size_campaign_revision,
)

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_ROOT = _ROOT / "qualification" / "p6-p5a6-compat"
_WORKSPACE = _FIXTURE_ROOT / "workspace"
_IDENTITY = _FIXTURE_ROOT / "P5A6_FIXTURE_IDENTITY.json"
_MANIFEST = _FIXTURE_ROOT / "P5A6_FIXTURE_CONTENT_MANIFEST.json"
_DATABASE = _FIXTURE_ROOT / "P5A6_FIXTURE_DATABASE_SNAPSHOT.json"

#: Derived material a legitimate real-owner *read* may materialize on demand
#: (executable shims and the restored normalized frame cache).  Nothing here is
#: persisted target-size, selection, CV, or final-production authority.
_DERIVED_PREFIXES = (
    "campaign/.mdstats/bin/",
    "campaign/.mdstats/frame-cache/",
)

#: Coordination infrastructure, not preserved evidence.  The campaign-state
#: writer lock is an empty advisory-lock pathname every writer flocks before
#: mutating; a reopen that takes it carries no scientific authority and changes
#: no persisted campaign content.
_DERIVED_SUFFIXES = (".writer-lock",)

#: The content-hash receipt cache is a low-level content/recipe cache whose
#: entries are recomputable from the files they describe.  It carries no
#: target-size, selection, CV, or final-production authority, so a real-owner
#: read may legitimately extend it.
_DERIVED_DATABASES = ("hash-receipts.sqlite3",)

_MISSING = (
    "The preserved P5A6 compatibility workspace is absent. Run the mandatory "
    "authenticated driver from a clean P6 checkout:\n"
    "  conda run -n mace python3 "
    "qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py\n"
    "It creates an ephemeral exact-baseline worktree and must be produced by "
    "P5A6 code, never by P6."
)


def _content_manifest(root: Path) -> tuple[str, dict[str, str]]:
    entries = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest(), entries


def _database_snapshot(root: Path) -> dict[str, dict[str, dict[str, object]]]:
    """Digest every persisted table, independently of SQLite page layout."""

    snapshot: dict[str, dict[str, dict[str, object]]] = {}
    for database in sorted(root.rglob("*.sqlite3")):
        if database.name in _DERIVED_DATABASES:
            continue
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            tables: dict[str, dict[str, object]] = {}
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ):
                rows = connection.execute(f"SELECT * FROM {name}").fetchall()
                tables[name] = {
                    "row_count": len(rows),
                    "content_digest": hashlib.sha256(
                        json.dumps(sorted(map(repr, rows))).encode()
                    ).hexdigest(),
                }
        finally:
            connection.close()
        snapshot[str(database.relative_to(root))] = tables
    return snapshot


def test_p6_fixture_provenance_is_recorded_and_bound_to_the_p5a6_baseline():
    """The recorded identity always exists, whether or not the workspace does."""

    identity = json.loads(_IDENTITY.read_text(encoding="utf-8"))
    assert identity["baseline_commit"] == "1670275487d29bbcde4c59efafdef9d1f8b0ced7"
    assert identity["baseline_tree"] == "17e2c5609974712bda1efd3375f09f42da830f68"
    assert identity["regime"] == "current"
    assert identity["lifecycle"] == "terminal_selected"
    assert int(identity["n_selected"]) > 0
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["content_manifest_digest"] == identity["content_manifest_digest"]
    assert manifest["file_count"] == identity["file_count"]
    database = json.loads(_DATABASE.read_text(encoding="utf-8"))
    assert "campaign/.mdstats/campaign.sqlite3" in database
    assert database["campaign/.mdstats/campaign.sqlite3"]["target_size_campaign_state"][
        "row_count"
    ] > 0
    builder = _FIXTURE_ROOT / "build_p5a6_compat_fixture.py"
    assert builder.is_file()


@pytest.mark.skipif(not _WORKSPACE.is_dir(), reason=_MISSING)
def test_p6_reopens_the_preserved_p5a6_workspace_through_real_owners():
    identity = json.loads(_IDENTITY.read_text(encoding="utf-8"))

    # 1. The workspace on disk is byte-for-byte what P5A6 produced.  This runs
    #    before anything opens the store, so it also proves that no P6 code
    #    rewrote, normalized, or migrated the persisted representation first.
    _, entries = _content_manifest(_WORKSPACE)
    recorded = json.loads(_MANIFEST.read_text(encoding="utf-8"))["files"]
    for name, sha in recorded.items():
        if name.endswith(".sqlite3"):
            continue
        assert entries.get(name) == sha, f"preserved P5A6 evidence changed: {name}"
    assert _database_snapshot(_WORKSPACE) == json.loads(
        _DATABASE.read_text(encoding="utf-8")
    ), "the preserved P5A6 campaign state was rewritten before the first P6 load"

    config = _WORKSPACE / "campaign.toml"

    # 2. Open it through the real production config loader and CampaignStore.
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = require_current_target_size_runtime(store)
        assert revision.state.regime is TargetSizeRegime.CURRENT
        assert revision.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
        assert revision.state.generation == identity["generation"]
        for field in (
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "experiment_definition_digest",
            "common_preparation_digest",
            "adopted_execution_head_digest",
        ):
            assert getattr(revision.state, field) == identity[field], field

        # 3. The P4 terminal selection and the exact selected-frame binding.
        terminal = revision.state.terminal
        assert terminal is not None
        assert terminal.selected_target_size == identity["n_selected"]
        assert terminal.selected_membership_digest == identity[
            "selected_membership_digest"
        ]
        selected = load_current_selected_training_context(cfg, paths, store)
        assert list(selected.selected_membership) == identity["selected_membership"]
        assert selected.binding.content_digest == identity["selected_binding_digest"]

        # 4. The persisted P5 method / CV / final-production identities.
        context = build_post_selection_context(cfg, paths, store, trainer=None)
        assert context.method.content_digest == identity["method_identity_digest"]
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        assert plan is not None and acceptance is not None and final_plan is not None
        assert plan.content_digest == identity["cv_plan_digest"]
        assert acceptance.content_digest == identity["cv_acceptance_digest"]
        assert acceptance.accepted
        assert final_plan.content_digest == identity["final_plan_digest"]
        assert final_plan.cv_authorization_digest == acceptance.content_digest
        assert final_plan.binding.content_digest == selected.binding.content_digest
    finally:
        store.close()

    # 5. Close and reopen: currentness survives a fresh store/process context.
    cfg2, paths2 = cli._load_config(config)
    store2 = CampaignStore(paths2.state_db)
    try:
        again = require_current_target_size_runtime(store2)
        assert again.state.content_digest == revision.state.content_digest
        selected2 = load_current_selected_training_context(cfg2, paths2, store2)
        assert selected2.binding.content_digest == identity["selected_binding_digest"]
        context2 = build_post_selection_context(cfg2, paths2, store2, trainer=None)
        assert (
            resolve_current_final_production_plan(context2).content_digest
            == identity["final_plan_digest"]
        )
    finally:
        store2.close()

    # 6. The reopen must not have mutated the preserved evidence.  Compare the
    #    persisted *content*: every table of every campaign database, and every
    #    preserved file that is not on-demand derived material.  SQLite page
    #    layout may legitimately churn while the stored rows do not.
    assert _database_snapshot(_WORKSPACE) == json.loads(
        _DATABASE.read_text(encoding="utf-8")
    ), "opening the preserved P5A6 workspace changed persisted campaign state"
    _, after = _content_manifest(_WORKSPACE)
    for name, sha in recorded.items():
        if name.endswith(".sqlite3"):
            continue
        assert after.get(name) == sha, f"preserved P5A6 evidence changed: {name}"
    unexpected = sorted(
        name
        for name in set(after) - set(recorded)
        if not name.startswith(_DERIVED_PREFIXES)
        and not name.endswith(_DERIVED_SUFFIXES)
    )
    assert not unexpected, f"the reopen wrote unexpected persisted files: {unexpected}"
