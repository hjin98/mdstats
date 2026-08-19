#!/usr/bin/env python3
"""Qualification-only production driver for DOC-MVSEL2-HARDEN1-V3.

This coordination helper never writes the production campaign. It clones the
production .mdstats state into qualification/tmp and exercises the frozen
candidate's existing campaign orchestration APIs there.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import time

from mdstats.training_data import campaign_cli as cli
from mdstats.training_data import mvsel2_hardening_runtime as hardening
from mdstats.training_data.target_coverage import TargetCoverageReference
from mdstats.training_data.target_coverage_sparse_index import TargetCoverageSparseIndex

EXPECTED_CANDIDATES = 36408
EXPECTED_FAMILIES = 165


def _copy_file(src: str, dst: str) -> str:
    source = Path(src)
    target = Path(dst)
    if source.suffix in {".sqlite", ".sqlite3", ".db"} or source.name.endswith(("-wal", "-shm")):
        return shutil.copy2(source, target)
    try:
        os.link(source, target)
        return str(target)
    except OSError:
        return shutil.copy2(source, target)


def _clone_internal(production_db: Path, root: Path) -> Path:
    source_internal = production_db.resolve().parent
    target_internal = root.resolve() / ".mdstats"
    if target_internal.exists():
        shutil.rmtree(target_internal)
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_internal, target_internal, copy_function=_copy_file)
    cloned_db = target_internal / production_db.name
    if not cloned_db.is_file():
        raise RuntimeError(f"cloned campaign database missing: {cloned_db}")
    return cloned_db


def _config_path(production_db: Path, explicit: str | None) -> Path:
    path = Path(explicit).expanduser().resolve() if explicit else production_db.resolve().parent.parent / "campaign.toml"
    if not path.is_file():
        raise RuntimeError(f"campaign configuration not found: {path}")
    return path


def _load(cloned_db: Path, config: Path):
    cfg, _ = cli._load_config(config)
    store = cli.CampaignStore(cloned_db)
    reference = store.get_record("target_coverage_reference", TargetCoverageReference)
    sparse = store.get_record("target_coverage_sparse_index", TargetCoverageSparseIndex)
    return cfg, store, reference, sparse


def _validate_domain(store, reference, sparse, domain: str) -> dict[str, object]:
    reference_domain = reference.domain(domain)
    forward = hardening._native_forward_view(store, sparse)
    forward_domain = forward.domain(domain)
    if forward_domain.candidate_count != EXPECTED_CANDIDATES:
        raise RuntimeError(
            f"candidate-count mismatch: expected={EXPECTED_CANDIDATES} actual={forward_domain.candidate_count}"
        )
    if len(forward_domain.families) != EXPECTED_FAMILIES:
        raise RuntimeError(
            f"family-count mismatch: expected={EXPECTED_FAMILIES} actual={len(forward_domain.families)}"
        )
    return {
        "domain": domain,
        "dataset_id": reference.dataset_id,
        "reference_digest": reference.content_digest,
        "mvidx1_content_digest": forward.mvidx1_content_digest,
        "candidate_count": forward_domain.candidate_count,
        "family_count": len(forward_domain.families),
        "frame_count": len(reference_domain.frame_uids),
    }


def _delete_v2_authority(store) -> None:
    db = store._connect()
    db.execute("DELETE FROM records WHERE key IN ('target_multi_view_selection_v2','target_multi_view_repair_v2')")
    db.execute("DELETE FROM records WHERE key LIKE 'target_multi_view_selection_state_v2:%'")
    db.commit()


def _delete_v1_authority(store) -> None:
    db = store._connect()
    db.execute("DELETE FROM records WHERE key IN ('target_multi_view_selection','target_multi_view_selection_state_cache','target_multi_view_repair')")
    db.commit()


def run_q5(args) -> int:
    production_db = Path(args.production_db).expanduser().resolve()
    config = _config_path(production_db, args.config)
    cloned_db = _clone_internal(production_db, Path(args.clone_root))
    cfg, store, reference, sparse = _load(cloned_db, config)
    try:
        identity = _validate_domain(store, reference, sparse, args.domain)
        _delete_v2_authority(store)
        started = time.perf_counter()
        uninterrupted, checkpoints = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        uninterrupted_seconds = time.perf_counter() - started
        uninterrupted_digest = uninterrupted.content_digest

        rows = store._connect().execute(
            "SELECT key FROM records WHERE key LIKE ?",
            (f"target_multi_view_selection_state_v2:{args.domain}:%",),
        ).fetchall()
        domain_rows = []
        for (key,) in rows:
            try:
                size = int(str(key).rsplit(":", 1)[1])
            except Exception:
                continue
            domain_rows.append((size, str(key)))
        if len(domain_rows) < 2:
            raise RuntimeError(f"need at least two MVSTATE2 checkpoints for corruption fallback, found {domain_rows}")
        domain_rows.sort(reverse=True)
        corrupted_size, corrupted_key = domain_rows[0]
        fallback_size = domain_rows[1][0]

        db = store._connect()
        db.execute("DELETE FROM records WHERE key='target_multi_view_selection_v2'")
        db.execute("UPDATE records SET payload='{}' WHERE key=?", (corrupted_key,))
        db.commit()

        started = time.perf_counter()
        resumed, resumed_pointers = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        resumed_seconds = time.perf_counter() - started
        resumed_digest = resumed.content_digest
        if resumed_digest != uninterrupted_digest:
            raise RuntimeError(
                f"resumed selector digest differs: uninterrupted={uninterrupted_digest} resumed={resumed_digest}"
            )

        result = {
            "schema": "mdstats.qualification.mvsel2-harden1-v3.q5.v1",
            "production_database": str(production_db),
            "ephemeral_database": str(cloned_db),
            "production_database_mutated": False,
            "identity": identity,
            "uninterrupted_selection_digest": uninterrupted_digest,
            "resumed_selection_digest": resumed_digest,
            "digest_equal": True,
            "uninterrupted_wall_seconds": uninterrupted_seconds,
            "resumed_wall_seconds": resumed_seconds,
            "generated_checkpoint_count": len(checkpoints),
            "corrupted_ephemeral_checkpoint_key": corrupted_key,
            "corrupted_checkpoint_size": corrupted_size,
            "expected_fallback_checkpoint_size": fallback_size,
            "resume_pointer_count": len(resumed_pointers),
            "native_forward_runtime": True,
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        return 0
    finally:
        store.close()


def _run_v1_chain(production_db: Path, config: Path, root: Path, domain: str) -> tuple[float, dict[str, object]]:
    cloned_db = _clone_internal(production_db, root)
    cfg, store, reference, sparse = _load(cloned_db, config)
    try:
        identity = _validate_domain(store, reference, sparse, domain)
        _delete_v1_authority(store)
        started = time.perf_counter()
        selection, state_cache = cli._ensure_target_multi_view_selection(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        repair = cli._ensure_target_multi_view_repair(
            store,
            cfg=cfg,
            coverage_reference=reference,
            sparse_index=sparse,
            selection_plan=selection,
            selection_state_cache=state_cache,
        )
        elapsed = time.perf_counter() - started
        return elapsed, {
            "identity": identity,
            "selection_digest": selection.content_digest,
            "repair_digest": repair.content_digest,
            "ephemeral_database": str(cloned_db),
        }
    finally:
        store.close()


def _run_v2_chain(production_db: Path, config: Path, root: Path, domain: str) -> tuple[float, dict[str, object]]:
    cloned_db = _clone_internal(production_db, root)
    cfg, store, reference, sparse = _load(cloned_db, config)
    try:
        identity = _validate_domain(store, reference, sparse, domain)
        _delete_v2_authority(store)
        started = time.perf_counter()
        selection, _ = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        repair = cli._ensure_target_multi_view_repair_v2(
            store,
            cfg=cfg,
            coverage_reference=reference,
            sparse_index=sparse,
            selection_plan=selection,
        )
        elapsed = time.perf_counter() - started
        return elapsed, {
            "identity": identity,
            "selection_digest": selection.content_digest,
            "repair_digest": repair.content_digest,
            "ephemeral_database": str(cloned_db),
        }
    finally:
        store.close()


def run_q7(args) -> int:
    production_db = Path(args.production_db).expanduser().resolve()
    config = _config_path(production_db, args.config)
    base = Path(args.clone_root).resolve()
    v1_seconds, v1 = _run_v1_chain(production_db, config, base / "v1", args.domain)
    v2_seconds, v2 = _run_v2_chain(production_db, config, base / "v2", args.domain)
    speedup = v1_seconds / v2_seconds if v2_seconds > 0 else float("inf")
    result = {
        "schema": "mdstats.qualification.mvsel2-harden1-v3.q7.v1",
        "production_database": str(production_db),
        "production_database_mutated": False,
        "domain": args.domain,
        "v1_chain_wall_seconds": v1_seconds,
        "v2_chain_wall_seconds": v2_seconds,
        "combined_chain_speedup": speedup,
        "required_speedup_floor": 10.0,
        "passes_speedup_floor": speedup >= 10.0,
        "v1": v1,
        "v2": v2,
        "stage_resource_scope": "candidate campaign orchestration wrappers for both chains",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return 0 if result["passes_speedup_floor"] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("q5", "q7"):
        p = sub.add_parser(name)
        p.add_argument("--production-db", required=True)
        p.add_argument("--domain", required=True)
        p.add_argument("--config")
        p.add_argument("--clone-root", required=True)
        p.add_argument("--output", required=True)
    args = parser.parse_args()
    return run_q5(args) if args.command == "q5" else run_q7(args)


if __name__ == "__main__":
    raise SystemExit(main())
