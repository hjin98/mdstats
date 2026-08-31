"""Authenticate and qualify the accepted P5A6 workspace against final P6.

The driver deliberately keeps the baseline producer and final reader in
separate Python processes and separate import roots.  It is the mandatory P6
compatibility command; unlike the optional developer test, it never skips
when the baseline worktree, producer, or preserved workspace cannot be made.

The baseline process uses the exact accepted P5A6 commit and only substitutes
the bounded numerical seams already accepted by P5.  The final process opens
the resulting disk workspace through the real current CampaignStore,
currentness, selected-binding, CV, and final-production owners without a
pre-load rewrite or migration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping


BASELINE_COMMIT = "1670275487d29bbcde4c59efafdef9d1f8b0ced7"
BASELINE_TREE = "17e2c5609974712bda1efd3375f09f42da830f68"
SCRIPT = Path(__file__).resolve()
FINAL_REPOSITORY = SCRIPT.parents[2]
ALLOWED_DERIVED_PREFIXES = (
    "campaign/.mdstats/bin/",
    "campaign/.mdstats/frame-cache/",
)
ALLOWED_DERIVED_DATABASE_NAMES = {"hash-receipts.sqlite3"}


class QualificationError(RuntimeError):
    """The authenticated compatibility qualification failed closed."""


def _git(*args: str, cwd: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise QualificationError(f"git authentication failed: {detail.strip()}") from exc
    return completed.stdout.strip()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _content_manifest(root: Path) -> tuple[str, dict[str, str]]:
    entries = {
        str(path.relative_to(root)): _sha256_bytes(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return _sha256_bytes(payload.encode("utf-8")), entries


def _database_snapshot(root: Path) -> dict[str, dict[str, dict[str, object]]]:
    """Digest SQLite table contents rather than mutable page layout."""

    snapshot: dict[str, dict[str, dict[str, object]]] = {}
    for database in sorted(root.rglob("*.sqlite3")):
        if database.name in ALLOWED_DERIVED_DATABASE_NAMES:
            continue
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            tables: dict[str, dict[str, object]] = {}
            names = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            for (name,) in names:
                rows = connection.execute(f"SELECT * FROM {name}").fetchall()
                tables[name] = {
                    "row_count": len(rows),
                    "content_digest": _sha256_bytes(
                        json.dumps(sorted(map(repr, rows))).encode("utf-8")
                    ),
                }
        finally:
            connection.close()
        snapshot[str(database.relative_to(root))] = tables
    return snapshot


def _inside(path: str | Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _assert_import_roots(root: Path) -> dict[str, str]:
    """Assert all baseline production owners resolve inside the baseline root."""

    import mdstats
    from mdstats.training_data import _campaign_cli_core
    from mdstats.training_data import campaign_post_selection
    from mdstats.training_data import campaign_post_selection_runtime
    from mdstats.training_data import campaign_target_size_runtime
    from mdstats.training_data import campaign_target_size_state
    from mdstats.training_data import target_size_execution
    import tests._mlff_post_selection_fixture as fixture

    modules = {
        "mdstats": mdstats,
        "mdstats.training_data._campaign_cli_core": _campaign_cli_core,
        "mdstats.training_data.campaign_target_size_state": campaign_target_size_state,
        "mdstats.training_data.campaign_target_size_runtime": campaign_target_size_runtime,
        "mdstats.training_data.campaign_post_selection": campaign_post_selection,
        "mdstats.training_data.campaign_post_selection_runtime": campaign_post_selection_runtime,
        "mdstats.training_data.target_size_execution": target_size_execution,
        "tests._mlff_post_selection_fixture": fixture,
    }
    locations: dict[str, str] = {}
    for name, module in modules.items():
        location = getattr(module, "__file__", None)
        if not location or not _inside(location, root):
            raise QualificationError(
                f"baseline import escaped authenticated worktree: {name} -> {location}"
            )
        locations[name] = str(Path(location).resolve())
    return locations


def _phase_produce(args: argparse.Namespace) -> int:
    baseline_root = Path(args.baseline_root).resolve()
    output_root = Path(args.output_root).resolve()
    if Path.cwd().resolve() != baseline_root:
        raise QualificationError(
            f"baseline producer cwd is not authenticated worktree: {Path.cwd()} != {baseline_root}"
        )
    if output_root.exists() and any(output_root.iterdir()):
        raise QualificationError(f"producer output must be empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    # This assertion is intentionally before build_selected_campaign creates
    # any config, source, SQLite, or target-size state.
    imported = _assert_import_roots(baseline_root)

    from tests._mlff_post_selection_fixture import (
        PostSelectionHarness,
        build_selected_campaign,
        run_cross_validate,
        run_train_production,
    )
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
    from mdstats.training_data.campaign_target_size_state import (
        load_target_size_campaign_revision,
    )

    config, workspace = build_selected_campaign(output_root)
    if run_cross_validate(config, PostSelectionHarness()) != 0:
        raise QualificationError("baseline P5A6 cross-validation owner failed")
    if run_train_production(config, PostSelectionHarness()) != 0:
        raise QualificationError("baseline P5A6 final-production owner failed")

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        terminal = revision.state.terminal
        if terminal is None:
            raise QualificationError("baseline producer did not publish terminal selection")
        selected = load_current_selected_training_context(cfg, paths, store)
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        if plan is None or acceptance is None or final_plan is None or not acceptance.accepted:
            raise QualificationError("baseline producer did not publish complete P5 identities")
        identity: dict[str, Any] = {
            "baseline_commit": _git("rev-parse", "HEAD", cwd=baseline_root),
            "baseline_tree": _git("rev-parse", "HEAD^{tree}", cwd=baseline_root),
            "imported_module_files": imported,
            "workspace_relative_path": str(workspace.relative_to(output_root)),
            "generation": revision.state.generation,
            "regime": revision.state.regime.value,
            "lifecycle": revision.state.lifecycle.value,
            "frame_authority_digest": revision.state.frame_authority_digest,
            "neutral_statistical_base_digest": revision.state.neutral_statistical_base_digest,
            "split_exclusion_digest": revision.state.split_exclusion_digest,
            "experiment_definition_digest": revision.state.experiment_definition_digest,
            "common_preparation_digest": revision.state.common_preparation_digest,
            "adopted_execution_head_digest": revision.state.adopted_execution_head_digest,
            "n_selected": terminal.selected_target_size,
            "selected_membership_digest": terminal.selected_membership_digest,
            "selected_membership": list(selected.selected_membership),
            "selected_binding_digest": selected.binding.content_digest,
            "method_identity_digest": context.method.content_digest,
            "cv_plan_digest": plan.content_digest,
            "cv_acceptance_digest": acceptance.content_digest,
            "final_plan_digest": final_plan.content_digest,
        }
    finally:
        store.close()

    manifest_digest, entries = _content_manifest(output_root)
    database = _database_snapshot(output_root)
    evidence_root = Path(args.evidence_root).resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)
    identity["content_manifest_digest"] = manifest_digest
    identity["file_count"] = len(entries)
    (evidence_root / "producer_identity.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (evidence_root / "producer_content_manifest.json").write_text(
        json.dumps(
            {"content_manifest_digest": manifest_digest, "file_count": len(entries), "files": entries},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence_root / "producer_database_snapshot.json").write_text(
        json.dumps(database, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


def _assert_preserved_content(
    root: Path,
    recorded_entries: Mapping[str, str],
    recorded_database: Mapping[str, Any],
) -> None:
    manifest_digest, entries = _content_manifest(root)
    expected_digest = _sha256_bytes(
        json.dumps(dict(sorted(recorded_entries.items())), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    if manifest_digest != expected_digest:
        for name, digest in recorded_entries.items():
            if name.endswith(".sqlite3"):
                continue
            if entries.get(name) != digest:
                raise QualificationError(f"preserved P5A6 file changed before/after P6 load: {name}")
        unexpected = sorted(
            name
            for name in set(entries) - set(recorded_entries)
            if not name.endswith(".sqlite3") and not name.startswith(ALLOWED_DERIVED_PREFIXES)
        )
        if unexpected:
            raise QualificationError(f"P6 wrote unexpected preserved files: {unexpected}")
    if _database_snapshot(root) != dict(recorded_database):
        raise QualificationError("P6 changed authoritative SQLite table content")


def _phase_reopen(args: argparse.Namespace) -> int:
    root = Path(args.workspace_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    identity = json.loads(Path(args.identity).read_text(encoding="utf-8"))
    recorded_manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    recorded_database = json.loads(Path(args.database).read_text(encoding="utf-8"))
    if not root.is_dir():
        raise QualificationError(f"authenticated P5A6 workspace is absent: {root}")
    _assert_preserved_content(root, recorded_manifest["files"], recorded_database)

    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data.campaign_post_selection import (
        load_current_selected_training_context,
    )
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_context,
        resolve_current_cv_acceptance,
        resolve_current_final_production_completion,
        resolve_current_final_production_plan,
    )
    from mdstats.training_data.campaign_target_size_cutover import (
        require_current_target_size_runtime,
    )
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeLifecycle,
        TargetSizeRegime,
    )

    config = root / "campaign.toml"
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = require_current_target_size_runtime(store)
        if revision.state.regime is not TargetSizeRegime.CURRENT:
            raise QualificationError("P5A6 workspace did not reopen as current")
        if revision.state.lifecycle is not TargetSizeLifecycle.TERMINAL_SELECTED:
            raise QualificationError("P5A6 workspace lost terminal selection on reopen")
        if revision.state.generation != identity["generation"]:
            raise QualificationError("P5A6 generation changed on first P6 load")
        for field in (
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "experiment_definition_digest",
            "common_preparation_digest",
            "adopted_execution_head_digest",
        ):
            if getattr(revision.state, field) != identity[field]:
                raise QualificationError(f"P5A6 {field} failed currentness authentication")
        terminal = revision.state.terminal
        if terminal is None or terminal.selected_target_size != identity["n_selected"]:
            raise QualificationError("P5A6 selected target failed authentication")
        if terminal.selected_membership_digest != identity["selected_membership_digest"]:
            raise QualificationError("P5A6 selected membership digest changed")
        selected = load_current_selected_training_context(cfg, paths, store)
        if list(selected.selected_membership) != identity["selected_membership"]:
            raise QualificationError("P5A6 selected membership sequence changed")
        if selected.binding.content_digest != identity["selected_binding_digest"]:
            raise QualificationError("P5A6 selected binding changed")
        context = build_post_selection_context(cfg, paths, store, trainer=None)
        acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        final_completion = resolve_current_final_production_completion(context)
        if context.method.content_digest != identity["method_identity_digest"]:
            raise QualificationError("P5A6 method identity changed")
        if acceptance is None or not acceptance.accepted:
            raise QualificationError("P5A6 CV acceptance is not current")
        if acceptance.content_digest != identity["cv_acceptance_digest"]:
            raise QualificationError("P5A6 CV acceptance digest changed")
        if final_plan is None or final_plan.content_digest != identity["final_plan_digest"]:
            raise QualificationError("P5A6 final-production identity changed")
        if final_plan.binding.content_digest != selected.binding.content_digest:
            raise QualificationError("P5A6 final-production binding changed")
        if final_completion is None:
            raise QualificationError("P5A6 final-production completion failed to resolve")
        revision_digest = revision.state.content_digest
    finally:
        store.close()

    # A second independent store/context proves restart currentness after the
    # first read has closed.  It is intentionally still read-only at the
    # scientific-owner boundary.
    cfg2, paths2 = cli._load_config(config)
    store2 = CampaignStore(paths2.state_db)
    try:
        again = require_current_target_size_runtime(store2)
        if again.state.content_digest != revision_digest:
            raise QualificationError("P5A6 currentness changed on second reopen")
        selected2 = load_current_selected_training_context(cfg2, paths2, store2)
        context2 = build_post_selection_context(cfg2, paths2, store2, trainer=None)
        final2 = resolve_current_final_production_plan(context2)
        completion2 = resolve_current_final_production_completion(context2)
        if selected2.binding.content_digest != identity["selected_binding_digest"]:
            raise QualificationError("P5A6 binding changed on second reopen")
        if final2 is None or final2.content_digest != identity["final_plan_digest"]:
            raise QualificationError("P5A6 final plan changed on second reopen")
        if completion2 is None:
            raise QualificationError("P5A6 final completion changed on second reopen")
    finally:
        store2.close()

    _assert_preserved_content(root, recorded_manifest["files"], recorded_database)
    (evidence_root / "reopen_result.json").write_text(
        json.dumps(
            {
                "workspace": str(root),
                "revision_digest": revision_digest,
                "preload_rewrite": False,
                "database_unchanged": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


def _phase_produce_p6(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise QualificationError(f"P6 producer output must be empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)

    from tests._mlff_post_selection_fixture import (
        PostSelectionHarness,
        build_selected_campaign,
        run_cross_validate,
        run_train_production,
    )
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data.campaign_post_selection import (
        load_current_selected_training_context,
    )
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_context,
        resolve_current_cv_acceptance,
        resolve_current_cv_plan,
        resolve_current_final_production_completion,
        resolve_current_final_production_plan,
    )
    from mdstats.training_data.campaign_target_size_state import (
        load_target_size_campaign_revision,
    )

    config, workspace = build_selected_campaign(output_root)
    harness = PostSelectionHarness()
    if run_cross_validate(config, harness) != 0:
        raise QualificationError("fresh P6 cross-validation execution failed")
    if run_train_production(config, harness) != 0:
        raise QualificationError("fresh P6 final-production execution failed")

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        terminal = revision.state.terminal
        if terminal is None:
            raise QualificationError("fresh P6 producer did not publish terminal selection")
        selected = load_current_selected_training_context(cfg, paths, store)
        context = build_post_selection_context(cfg, paths, store, trainer=object())
        plan = resolve_current_cv_plan(context)
        acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        final_completion = resolve_current_final_production_completion(context)
        if (
            plan is None
            or acceptance is None
            or not acceptance.accepted
            or final_plan is None
            or final_completion is None
        ):
            raise QualificationError("fresh P6 producer did not achieve full final production completion")
        identity: dict[str, Any] = {
            "workspace_relative_path": str(workspace.relative_to(output_root)),
            "generation": revision.state.generation,
            "regime": revision.state.regime.value,
            "lifecycle": revision.state.lifecycle.value,
            "frame_authority_digest": revision.state.frame_authority_digest,
            "neutral_statistical_base_digest": revision.state.neutral_statistical_base_digest,
            "split_exclusion_digest": revision.state.split_exclusion_digest,
            "experiment_definition_digest": revision.state.experiment_definition_digest,
            "common_preparation_digest": revision.state.common_preparation_digest,
            "adopted_execution_head_digest": revision.state.adopted_execution_head_digest,
            "n_selected": terminal.selected_target_size,
            "selected_membership_digest": terminal.selected_membership_digest,
            "selected_membership": list(selected.selected_membership),
            "selected_binding_digest": selected.binding.content_digest,
            "method_identity_digest": context.method.content_digest,
            "cv_plan_digest": plan.content_digest,
            "cv_acceptance_digest": acceptance.content_digest,
            "final_plan_digest": final_plan.content_digest,
            "final_completion_digest": final_completion.content_digest,
        }
    finally:
        store.close()

    manifest_digest, entries = _content_manifest(output_root)
    database = _database_snapshot(output_root)
    identity["content_manifest_digest"] = manifest_digest
    identity["file_count"] = len(entries)
    (evidence_root / "producer_p6_identity.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (evidence_root / "producer_p6_content_manifest.json").write_text(
        json.dumps(
            {"content_manifest_digest": manifest_digest, "file_count": len(entries), "files": entries},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence_root / "producer_p6_database_snapshot.json").write_text(
        json.dumps(database, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


def _phase_reopen_p6(args: argparse.Namespace) -> int:
    root = Path(args.workspace_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    identity = json.loads(Path(args.identity).read_text(encoding="utf-8"))
    recorded_manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    recorded_database = json.loads(Path(args.database).read_text(encoding="utf-8"))
    if not root.is_dir():
        raise QualificationError(f"authenticated fresh P6 workspace is absent: {root}")
    _assert_preserved_content(root, recorded_manifest["files"], recorded_database)

    from tests._mlff_post_selection_fixture import (
        PostSelectionHarness,
        run_cross_validate,
        run_train_production,
    )
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data.campaign_post_selection import (
        load_current_selected_training_context,
    )
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_context,
        resolve_current_cv_acceptance,
        resolve_current_final_production_completion,
        resolve_current_final_production_plan,
    )
    from mdstats.training_data.campaign_target_size_cutover import (
        require_current_target_size_runtime,
    )
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeLifecycle,
        TargetSizeRegime,
    )

    config = root / "campaign.toml"
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        revision = require_current_target_size_runtime(store)
        if revision.state.regime is not TargetSizeRegime.CURRENT:
            raise QualificationError("P6 workspace did not reopen as current")
        if revision.state.lifecycle is not TargetSizeLifecycle.TERMINAL_SELECTED:
            raise QualificationError("P6 workspace lost terminal selection on reopen")
        if revision.state.generation != identity["generation"]:
            raise QualificationError("P6 generation changed on reopen")
        for field in (
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "experiment_definition_digest",
            "common_preparation_digest",
            "adopted_execution_head_digest",
        ):
            if getattr(revision.state, field) != identity[field]:
                raise QualificationError(f"P6 {field} failed currentness authentication")
        terminal = revision.state.terminal
        if terminal is None or terminal.selected_target_size != identity["n_selected"]:
            raise QualificationError("P6 selected target failed authentication")
        if terminal.selected_membership_digest != identity["selected_membership_digest"]:
            raise QualificationError("P6 selected membership digest changed")
        selected = load_current_selected_training_context(cfg, paths, store)
        if list(selected.selected_membership) != identity["selected_membership"]:
            raise QualificationError("P6 selected membership sequence changed")
        if selected.binding.content_digest != identity["selected_binding_digest"]:
            raise QualificationError("P6 selected binding changed")
        context = build_post_selection_context(cfg, paths, store, trainer=None)
        acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        final_completion = resolve_current_final_production_completion(context)
        if context.method.content_digest != identity["method_identity_digest"]:
            raise QualificationError("P6 method identity changed")
        if acceptance is None or not acceptance.accepted:
            raise QualificationError("P6 CV acceptance is not current")
        if acceptance.content_digest != identity["cv_acceptance_digest"]:
            raise QualificationError("P6 CV acceptance digest changed")
        if final_plan is None or final_plan.content_digest != identity["final_plan_digest"]:
            raise QualificationError("P6 final-production identity changed")
        if final_completion is None or final_completion.content_digest != identity["final_completion_digest"]:
            raise QualificationError("P6 final-production completion digest changed on reopen")
        revision_digest = revision.state.content_digest
    finally:
        store.close()

    # Rerun cross-validate and train-production with an instrumented harness.
    # Already complete authenticated runs must be reused rather than retrained.
    instrumented_harness = PostSelectionHarness()
    rc_cv = run_cross_validate(config, instrumented_harness)
    if rc_cv != 0:
        raise QualificationError("P6 cross-validate rerun failed")
    rc_prod = run_train_production(config, instrumented_harness)
    if rc_prod != 0:
        raise QualificationError("P6 train-production rerun failed")
    if len(instrumented_harness.runs) != 0:
        raise QualificationError(
            f"P6 rerun re-executed training for {len(instrumented_harness.runs)} run(s) "
            "instead of reusing authenticated complete evidence."
        )

    # Verify completion still authenticates after rerun
    cfg2, paths2 = cli._load_config(config)
    store2 = CampaignStore(paths2.state_db)
    try:
        context2 = build_post_selection_context(cfg2, paths2, store2, trainer=None)
        completion2 = resolve_current_final_production_completion(context2)
        if completion2 is None or completion2.content_digest != identity["final_completion_digest"]:
            raise QualificationError("P6 completion digest changed after idempotent rerun")
    finally:
        store2.close()

    (evidence_root / "p6_reopen_result.json").write_text(
        json.dumps(
            {
                "workspace": str(root),
                "revision_digest": revision_digest,
                "completion_digest": identity["final_completion_digest"],
                "training_reruns_executed": len(instrumented_harness.runs),
                "reused_successfully": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


def _phase_reject(args: argparse.Namespace) -> int:
    root = Path(args.output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data.campaign_target_size_cutover import (
        TargetSizeCutoverError,
        require_current_target_size_runtime,
    )

    database = root / "retired.sqlite3"
    store = CampaignStore(database)
    try:
        store.put_record(
            "target_size_study",
            {
                "schema": "obsolete-derived-target-size",
                "selected_target_size": 8192,
                "qualified_sizes": [128, 256, 512],
            },
        )
        try:
            require_current_target_size_runtime(store)
        except TargetSizeCutoverError:
            pass
        else:
            raise QualificationError("retired target-size state was accepted")
        if not store.has_record("target_size_study"):
            raise QualificationError("reject path mutated retired state before reuse")
    finally:
        store.close()
    return 0


def _phase_environment(phase: str, args: argparse.Namespace) -> int:
    if phase == "produce":
        return _phase_produce(args)
    if phase == "reopen":
        return _phase_reopen(args)
    if phase == "produce_p6":
        return _phase_produce_p6(args)
    if phase == "reopen_p6":
        return _phase_reopen_p6(args)
    if phase == "reject":
        return _phase_reject(args)
    raise QualificationError(f"unknown qualification phase: {phase}")


def _run_phase(
    command: list[str], *, cwd: Path, env: Mapping[str, str]
) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, str(exc)
    if completed.returncode == 0:
        return True, completed.stdout
    return False, (completed.stdout + "\n" + completed.stderr).strip()


def _orchestrate(args: argparse.Namespace) -> int:
    output_arg = Path(args.output_dir).resolve() if args.output_dir else None
    if output_arg is not None:
        if output_arg.exists() and any(output_arg.iterdir()):
            raise QualificationError(f"--output-dir must be empty: {output_arg}")
        output_arg.mkdir(parents=True, exist_ok=True)

    temp_context: tempfile.TemporaryDirectory[str] | None = None
    if output_arg is None:
        temp_context = tempfile.TemporaryDirectory(prefix="mdstats-p6-p5a6-")
        output_root = Path(temp_context.name).resolve()
    else:
        output_root = output_arg
    evidence_root = output_root / "evidence"
    producer_root = output_root / "producer"
    producer_p6_root = output_root / "producer-p6"
    reject_root = output_root / "reject"
    baseline_root = output_root / "baseline-worktree"
    worktree_added = False
    statuses = {
        "P5A6 -> P6 authenticated current-generation compatibility": False,
        "P6 -> P6 current-generation restart": False,
        "V5/V6 -> reject-before-reuse": False,
    }
    details: list[str] = []
    try:
        commit = _git("rev-parse", BASELINE_COMMIT, cwd=FINAL_REPOSITORY)
        if commit != BASELINE_COMMIT:
            raise QualificationError(f"baseline commit does not resolve exactly: {commit}")
        try:
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(baseline_root), BASELINE_COMMIT],
                cwd=FINAL_REPOSITORY,
                check=True,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or str(exc)
            raise QualificationError(f"baseline worktree creation failed: {detail.strip()}") from exc
        worktree_added = True
        actual_commit = _git("rev-parse", "HEAD", cwd=baseline_root)
        actual_tree = _git("rev-parse", "HEAD^{tree}", cwd=baseline_root)
        if actual_commit != BASELINE_COMMIT or actual_tree != BASELINE_TREE:
            raise QualificationError(
                "authenticated baseline identity mismatch: "
                f"commit={actual_commit} tree={actual_tree}"
            )

        baseline_env = os.environ.copy()
        baseline_env["PYTHONPATH"] = str(baseline_root)
        produce_ok, produce_detail = _run_phase(
            [
                sys.executable,
                str(SCRIPT),
                "--phase",
                "produce",
                "--baseline-root",
                str(baseline_root),
                "--output-root",
                str(producer_root),
                "--evidence-root",
                str(evidence_root),
            ],
            cwd=baseline_root,
            env=baseline_env,
        )
        if not produce_ok:
            details.append("P5A6 producer failed:\n" + produce_detail)

        final_env = os.environ.copy()
        final_env["PYTHONPATH"] = str(FINAL_REPOSITORY)
        if produce_ok:
            reopen_ok, reopen_detail = _run_phase(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--phase",
                    "reopen",
                    "--workspace-root",
                    str(producer_root),
                    "--identity",
                    str(evidence_root / "producer_identity.json"),
                    "--manifest",
                    str(evidence_root / "producer_content_manifest.json"),
                    "--database",
                    str(evidence_root / "producer_database_snapshot.json"),
                    "--evidence-root",
                    str(evidence_root),
                ],
                cwd=FINAL_REPOSITORY,
                env=final_env,
            )
            if not reopen_ok:
                details.append("P6 reopen failed:\n" + reopen_detail)
            else:
                statuses["P5A6 -> P6 authenticated current-generation compatibility"] = True
        else:
            details.append("P6 reopen not attempted because baseline production failed")

        produce_p6_ok, produce_p6_detail = _run_phase(
            [
                sys.executable,
                str(SCRIPT),
                "--phase",
                "produce_p6",
                "--output-root",
                str(producer_p6_root),
                "--evidence-root",
                str(evidence_root),
            ],
            cwd=FINAL_REPOSITORY,
            env=final_env,
        )
        if not produce_p6_ok:
            details.append("Fresh P6 producer failed:\n" + produce_p6_detail)
        else:
            reopen_p6_ok, reopen_p6_detail = _run_phase(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--phase",
                    "reopen_p6",
                    "--workspace-root",
                    str(producer_p6_root),
                    "--identity",
                    str(evidence_root / "producer_p6_identity.json"),
                    "--manifest",
                    str(evidence_root / "producer_p6_content_manifest.json"),
                    "--database",
                    str(evidence_root / "producer_p6_database_snapshot.json"),
                    "--evidence-root",
                    str(evidence_root),
                ],
                cwd=FINAL_REPOSITORY,
                env=final_env,
            )
            if not reopen_p6_ok:
                details.append("Fresh P6 reopen/restart failed:\n" + reopen_p6_detail)
            else:
                statuses["P6 -> P6 current-generation restart"] = True

        reject_ok, reject_detail = _run_phase(
            [
                sys.executable,
                str(SCRIPT),
                "--phase",
                "reject",
                "--output-root",
                str(reject_root),
            ],
            cwd=FINAL_REPOSITORY,
            env=final_env,
        )
        if not reject_ok:
            details.append("V5/V6 reject phase failed:\n" + reject_detail)
        else:
            statuses["V5/V6 -> reject-before-reuse"] = True
    finally:
        if worktree_added:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(baseline_root)],
                cwd=FINAL_REPOSITORY,
                check=False,
                capture_output=True,
                text=True,
            )
        if temp_context is not None:
            temp_context.cleanup()

    for label, passed in statuses.items():
        print(f"{label}: {'PASS' if passed else 'FAIL'}")
    if details:
        print("\n".join(details), file=sys.stderr)
    if not all(statuses.values()):
        return 1
    if output_arg is not None:
        print(f"qualification evidence retained at {output_arg}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("produce", "reopen", "produce_p6", "reopen_p6", "reject"),
        help="internal phase; omit it to run the mandatory three-case qualification",
    )
    parser.add_argument("--output-dir", help="optional empty directory in which to retain evidence")
    parser.add_argument("--baseline-root")
    parser.add_argument("--output-root")
    parser.add_argument("--evidence-root")
    parser.add_argument("--workspace-root")
    parser.add_argument("--identity")
    parser.add_argument("--manifest")
    parser.add_argument("--database")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.phase is None:
            return _orchestrate(args)
        required = {
            "produce": (args.baseline_root, args.output_root, args.evidence_root),
            "reopen": (
                args.workspace_root,
                args.identity,
                args.manifest,
                args.database,
                args.evidence_root,
            ),
            "produce_p6": (args.output_root, args.evidence_root),
            "reopen_p6": (
                args.workspace_root,
                args.identity,
                args.manifest,
                args.database,
                args.evidence_root,
            ),
            "reject": (args.output_root,),
        }[args.phase]
        if any(value is None for value in required):
            raise QualificationError(f"phase {args.phase} is missing required arguments")
        return _phase_environment(args.phase, args)
    except QualificationError as exc:
        print(f"qualification failed closed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
