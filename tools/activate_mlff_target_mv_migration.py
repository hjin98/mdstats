#!/usr/bin/env python3
"""Atomically activate the FINAL-GPU1-qualified TARGET-DATA2C v5 migration.

The command is intentionally two-phase.  A default dry-run authenticates the
FINAL-GPU1 v2 qualification against the campaign's frozen MVMIGRATE1 upstreams
and reconstructs the exact v5/v3 replacement records.  ``--apply`` publishes
those records in one SQLite transaction, preserving the historical v4 ladder
and deleting only stale generation-dependent aliases.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mdstats
from mdstats.training_data.campaign_cli import (
    CampaignCliError,
    CampaignStore,
    _load_config,
    _target_coverage_query_workers,
    _target_size_convergence_policy,
)

SCHEMA = "mdstats.target-mv-migration-activation-cli.v1"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise CampaignCliError(f"Expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def _load_campaign_authorities(store: CampaignStore) -> dict[str, Any]:
    legacy_key = (
        "target_data_ladder_legacy_v4"
        if store.has_record("target_multi_view_migration_activation")
        else "target_data_ladder"
    )
    authorities = {
        "role_freeze": store.get_record("target_data_role_freeze", mdstats.TargetDataRoleFreeze),
        "reference": store.get_record("target_coverage_reference", mdstats.TargetCoverageReference),
        "repair": store.get_record("target_multi_view_repair", mdstats.TargetMultiViewRepairPlan),
        "qualification": store.get_record("target_multi_view_qualification", mdstats.TargetMultiViewQualificationPlan),
        "size_halve2": store.get_record("size_halve2_plan", mdstats.SizeHalve2Plan),
        "size_fidelity2_plan": store.get_record("size_fidelity2_execution_plan", mdstats.SizeFidelity2ExecutionPlan),
        "legacy_ladder": store.get_record(legacy_key, mdstats.TargetDataLadderPlan),
    }
    if authorities["legacy_ladder"].authority_version != mdstats.TARGET_DATA_LADDER_VERSION:
        raise CampaignCliError("MVMIGRATE1 activation requires the preserved TARGET-DATA2C v4 authority.")
    mdstats.validate_target_data_ladder_authority(
        authorities["legacy_ladder"],
        reference=authorities["reference"],
        target_data_role_freeze=authorities["role_freeze"],
    )
    return authorities


def _authenticate_final_gpu1(
    qualification_path: Path,
    *,
    size_fidelity2_path: Path | None,
    mv_learning_control_path: Path | None,
) -> tuple[Any, Any, Any]:
    final = mdstats.FinalGpu1QualificationRecord.from_dict(_read_json(qualification_path))
    if final.policy.authority_version != mdstats.FINAL_GPU1_VERSION:
        raise CampaignCliError(
            "MVMIGRATE1 activation requires the current FINAL-GPU1 v2 qualification authority."
        )
    if not final.passed:
        raise CampaignCliError(
            "FINAL-GPU1 qualification did not pass: " + ", ".join(final.blocking_reasons)
        )
    if final.size_fidelity2 is None or final.target_mv_learning_control is None:
        raise CampaignCliError("FINAL-GPU1 v2 is missing typed MVMIGRATE1 qualification records.")

    fidelity = final.size_fidelity2
    learning = final.target_mv_learning_control
    if size_fidelity2_path is not None:
        supplied = mdstats.SizeFidelity2QualificationReport.from_dict(_read_json(size_fidelity2_path))
        if supplied.content_digest != fidelity.content_digest:
            raise CampaignCliError("Supplied SIZE-FIDELITY2 report differs from FINAL-GPU1 typed evidence.")
        fidelity = supplied
    if mv_learning_control_path is not None:
        supplied = mdstats.TargetMultiViewLearningControlReport.from_dict(_read_json(mv_learning_control_path))
        if supplied.content_digest != learning.content_digest:
            raise CampaignCliError("Supplied MVMIGRATE1 learning report differs from FINAL-GPU1 typed evidence.")
        learning = supplied
    return final, fidelity, learning


def _build_activation(
    *,
    cfg: dict[str, Any],
    store: CampaignStore,
    final_gpu1: Any,
    fidelity: Any,
    learning: Any,
) -> tuple[Any, Any, Any, Any, dict[str, Any]]:
    upstream = _load_campaign_authorities(store)
    legacy = upstream["legacy_ladder"]
    if fidelity.dataset_id != legacy.dataset_id or learning.dataset_id != legacy.dataset_id:
        raise CampaignCliError("FINAL-GPU1 MVMIGRATE1 evidence does not belong to this campaign dataset.")

    migration = mdstats.build_target_multi_view_migration_plan(
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=upstream["repair"],
        target_multi_view_qualification=upstream["qualification"],
        size_halve2_plan=upstream["size_halve2"],
        size_fidelity2_execution_plan=upstream["size_fidelity2_plan"],
        learning_control_report=learning,
        size_fidelity2_qualification=fidelity,
    )
    mdstats.validate_target_multi_view_migration_plan(
        migration,
        legacy_target_data_ladder=legacy,
        target_multi_view_repair=upstream["repair"],
        target_multi_view_qualification=upstream["qualification"],
        size_halve2_plan=upstream["size_halve2"],
        size_fidelity2_execution_plan=upstream["size_fidelity2_plan"],
        learning_control_report=learning,
        size_fidelity2_qualification=fidelity,
    )
    if not migration.activation_authorized:
        raise CampaignCliError(f"MVMIGRATE1 activation remains blocked: {migration.decision_reason}")

    coverage_workers, _ = _target_coverage_query_workers(cfg)
    migrated = mdstats.build_migrated_target_data_ladder(
        upstream["reference"],
        upstream["role_freeze"],
        target_multi_view_repair=upstream["repair"],
        target_multi_view_qualification=upstream["qualification"],
        migration_authority_digest=migration.content_digest,
        coverage_query_workers=coverage_workers,
    )
    mdstats.validate_migrated_target_data_ladder_authority(
        migrated,
        reference=upstream["reference"],
        target_data_role_freeze=upstream["role_freeze"],
        target_multi_view_repair=upstream["repair"],
        target_multi_view_qualification=upstream["qualification"],
        migration_authority_digest=migration.content_digest,
        coverage_query_workers=coverage_workers,
    )
    convergence_policy = _target_size_convergence_policy(cfg, ladder=migrated)
    convergence = mdstats.build_target_size_convergence_plan(migrated, policy=convergence_policy)
    mdstats.validate_target_size_convergence_authority(convergence, ladder=migrated)

    prior_prod_digest = (
        store.record_digest("target_production_corpus_decision")
        if store.has_record("target_production_corpus_decision")
        else None
    )
    activation = mdstats.TargetMultiViewMigrationActivation(
        dataset_id=migrated.dataset_id,
        final_gpu1_qualification_digest=final_gpu1.content_digest,
        learning_control_report_digest=learning.content_digest,
        size_fidelity2_qualification_digest=fidelity.content_digest,
        migration_plan_digest=migration.content_digest,
        legacy_target_data_ladder_digest=legacy.content_digest,
        migrated_target_data_ladder_digest=migrated.content_digest,
        migrated_target_size_convergence_digest=convergence.content_digest,
        prior_target_production_corpus_digest=prior_prod_digest,
    )
    summary = {
        "schema": SCHEMA,
        "status": "ready_for_atomic_activation",
        "dataset_id": migrated.dataset_id,
        "final_gpu1_qualification_digest": final_gpu1.content_digest,
        "migration_plan_digest": migration.content_digest,
        "legacy_target_data_ladder_digest": legacy.content_digest,
        "migrated_target_data_ladder_digest": migrated.content_digest,
        "migrated_target_size_convergence_digest": convergence.content_digest,
        "activation_receipt_digest": activation.content_digest,
        "fixed_target_sizes": list(migrated.configured_candidate_sizes),
        "hard_qualified_sizes": list(convergence.stage_a_survivor_sizes),
        "minimum_hard_qualifiers": convergence.policy.min_coverage_qualifiers,
        "prior_target_production_corpus_digest": prior_prod_digest,
    }
    return migration, migrated, convergence, activation, summary


def activate(args: argparse.Namespace) -> int:
    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    try:
        final, fidelity, learning = _authenticate_final_gpu1(
            Path(args.final_gpu1).expanduser().resolve(),
            size_fidelity2_path=(None if args.size_fidelity2 is None else Path(args.size_fidelity2).expanduser().resolve()),
            mv_learning_control_path=(None if args.mv_learning_control is None else Path(args.mv_learning_control).expanduser().resolve()),
        )
        migration, migrated, convergence, activation, summary = _build_activation(
            cfg=cfg,
            store=store,
            final_gpu1=final,
            fidelity=fidelity,
            learning=learning,
        )

        existing = store.get_record_optional(
            "target_multi_view_migration_activation", mdstats.TargetMultiViewMigrationActivation
        )
        if existing is not None:
            if existing.content_digest != activation.content_digest:
                raise CampaignCliError(
                    "Campaign is already activated under a different MVMIGRATE1 receipt; refusing replacement."
                )
            live = store.get_record("target_data_ladder", mdstats.TargetDataLadderPlan)
            current_d = store.get_record("target_size_convergence", mdstats.TargetSizeConvergencePlan)
            if live.content_digest != migrated.content_digest or current_d.content_digest != convergence.content_digest:
                raise CampaignCliError("Existing activation receipt does not match live v5/v3 aliases.")
            summary["status"] = "already_activated"
        elif args.apply:
            legacy = store.get_record("target_data_ladder", mdstats.TargetDataLadderPlan)
            store.replace_records_atomically(
                {
                    "final_gpu1_qualification": final,
                    "target_multi_view_learning_control_qualification": learning,
                    "size_fidelity2_qualification": fidelity,
                    "target_multi_view_migration_plan": migration,
                    "target_data_ladder_mv_candidate": migrated,
                    "target_data_ladder_legacy_v4": legacy,
                    "target_data_ladder": migrated,
                    "target_size_convergence": convergence,
                    "target_multi_view_migration_activation": activation,
                },
                delete_keys=("target_production_corpus_decision", "prepare_restart_receipt"),
            )
            summary["status"] = "activated"
        else:
            summary["status"] = "dry_run_passed"

        output = (
            Path(args.output).expanduser().resolve()
            if args.output
            else paths.results / "target-mv-migration-activation.json"
        )
        _write_json(output, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    finally:
        store.close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", required=True, help="Campaign TOML")
    result.add_argument("--final-gpu1", required=True, help="Passing FINAL-GPU1 v2 qualification JSON")
    result.add_argument("--size-fidelity2", help="Optional explicit SIZE-FIDELITY2 report; must match FINAL-GPU1")
    result.add_argument("--mv-learning-control", help="Optional explicit MV learning-control report; must match FINAL-GPU1")
    result.add_argument("--output", help="Activation/dry-run receipt JSON")
    result.add_argument("--apply", action="store_true", help="Publish the authenticated v5/v3 generation atomically")
    return result


def main() -> int:
    try:
        return activate(parser().parse_args())
    except (CampaignCliError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
