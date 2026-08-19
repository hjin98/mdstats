#!/usr/bin/env python3
"""Qualification-only production driver for MVSEL2/REPAIR2 hardening.

All production campaign data are treated as read-only. Every measurement or
preparation uses a physically copied, disjoint scratch snapshot. This helper
contains no product authority and may be adjusted for equivalent operational
paths without changing the frozen qualification semantics.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
from statistics import median
import time

from mdstats.training_data import campaign_cli as cli
from mdstats.training_data import mvsel2_hardening_runtime as hardening
from mdstats.training_data.target_coverage import TargetCoverageReference
from mdstats.training_data.target_coverage_sparse_index import TargetCoverageSparseIndex

EXPECTED_CANDIDATES = 36408
EXPECTED_FAMILIES = 165
SPEEDUP_FLOOR = 10.0


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _assert_safe_clone_root(production_db: Path, root: Path) -> tuple[Path, Path]:
    source_internal = production_db.resolve().parent
    target_internal = root.expanduser().resolve() / ".mdstats"
    if (
        target_internal == source_internal
        or _is_relative_to(target_internal, source_internal)
        or _is_relative_to(source_internal, target_internal)
    ):
        raise RuntimeError(
            "qualification clone must be disjoint from production .mdstats: "
            f"source={source_internal} target={target_internal}"
        )
    return source_internal, target_internal


def _copy_file(src: str, dst: str) -> str:
    return shutil.copy2(src, dst)


def _clone_internal(production_db: Path, root: Path) -> Path:
    source_internal, target_internal = _assert_safe_clone_root(production_db, root)
    if target_internal.exists():
        shutil.rmtree(target_internal)
    target_internal.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_internal, target_internal, copy_function=_copy_file)
    cloned_db = target_internal / production_db.name
    if not cloned_db.is_file():
        raise RuntimeError(f"cloned campaign database missing: {cloned_db}")
    return cloned_db


def _require_config(path_text: str) -> Path:
    path = Path(path_text).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"campaign configuration not found: {path}")
    return path


def _load(cloned_db: Path, config: Path):
    cfg, _ = cli._load_config(config)
    store = cli.CampaignStore(cloned_db)
    reference = store.get_record("target_coverage_reference", TargetCoverageReference)
    sparse = store.get_record(
        "target_coverage_sparse_index", TargetCoverageSparseIndex
    )
    return cfg, store, reference, sparse


def _validate_domain(store, reference, sparse, domain: str) -> dict[str, object]:
    reference_domain = reference.domain(domain)
    forward = hardening._native_forward_view(store, sparse)
    forward_domain = forward.domain(domain)
    if forward_domain.candidate_count != EXPECTED_CANDIDATES:
        raise RuntimeError(
            f"candidate-count mismatch: expected={EXPECTED_CANDIDATES} "
            f"actual={forward_domain.candidate_count}"
        )
    if len(forward_domain.families) != EXPECTED_FAMILIES:
        raise RuntimeError(
            f"family-count mismatch: expected={EXPECTED_FAMILIES} "
            f"actual={len(forward_domain.families)}"
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
    db.execute(
        "DELETE FROM records WHERE key IN "
        "('target_multi_view_selection_v2','target_multi_view_repair_v2')"
    )
    db.execute(
        "DELETE FROM records WHERE key LIKE 'target_multi_view_selection_state_v2:%'"
    )
    db.commit()


def _delete_v1_authority(store) -> None:
    db = store._connect()
    db.execute(
        "DELETE FROM records WHERE key IN "
        "('target_multi_view_selection','target_multi_view_selection_state_cache',"
        "'target_multi_view_repair')"
    )
    db.commit()


def run_q6_prepare(args) -> int:
    production_db = Path(args.production_db).expanduser().resolve()
    if not production_db.is_file():
        raise RuntimeError(f"production database not found: {production_db}")
    config = _require_config(args.config)
    cloned_db = _clone_internal(production_db, Path(args.clone_root))
    cfg, store, reference, sparse = _load(cloned_db, config)
    try:
        identity = _validate_domain(store, reference, sparse, args.domain)
        _delete_v2_authority(store)
        started = time.perf_counter()
        selection, checkpoint_pointers = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        elapsed = time.perf_counter() - started
        prefix = f"target_multi_view_selection_state_v2:{args.domain}:"
        checkpoint_count = sum(
            1 for key in checkpoint_pointers if str(key).startswith(prefix)
        )
        if checkpoint_count == 0:
            raise RuntimeError(
                "fresh Q6 preparation produced no MVSTATE2 checkpoints for target domain"
            )
        result = {
            "schema": "mdstats.qualification.mvsel2-harden1-v3.q6-prepare.v1",
            "production_database": str(production_db),
            "ephemeral_database": str(cloned_db),
            "config": str(config),
            "identity": identity,
            "selection_digest": selection.content_digest,
            "checkpoint_count": checkpoint_count,
            "preparation_wall_seconds": elapsed,
            "copy_only_snapshot": True,
            "native_forward_runtime": True,
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        return 0
    finally:
        store.close()


def _run_v1_chain(
    production_db: Path, config: Path, root: Path, domain: str
) -> tuple[float, dict[str, object]]:
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


def _run_v2_chain(
    production_db: Path, config: Path, root: Path, domain: str
) -> tuple[float, dict[str, object]]:
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


def _resource_context() -> dict[str, object]:
    affinity = None
    if hasattr(os, "sched_getaffinity"):
        try:
            affinity = sorted(os.sched_getaffinity(0))
        except OSError:
            affinity = None
    return {
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
        "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
        "cpu_affinity": affinity,
    }


def _measure_pair(
    production_db: Path,
    config: Path,
    base: Path,
    domain: str,
    pair_index: int,
) -> dict[str, object]:
    pair_root = base / f"pair-{pair_index}"
    v1_seconds, v1 = _run_v1_chain(
        production_db, config, pair_root / "v1", domain
    )
    v2_seconds, v2 = _run_v2_chain(
        production_db, config, pair_root / "v2", domain
    )
    speedup = v1_seconds / v2_seconds if v2_seconds > 0 else float("inf")
    return {
        "pair": pair_index,
        "v1_chain_wall_seconds": v1_seconds,
        "v2_chain_wall_seconds": v2_seconds,
        "speedup": speedup,
        "v1": v1,
        "v2": v2,
    }


def run_q7(args) -> int:
    production_db = Path(args.production_db).expanduser().resolve()
    if not production_db.is_file():
        raise RuntimeError(f"production database not found: {production_db}")
    config = _require_config(args.config)
    base = Path(args.clone_root).expanduser().resolve()
    _assert_safe_clone_root(production_db, base / "pair-1" / "v1")

    resource_context = _resource_context()
    measurements = [
        _measure_pair(production_db, config, base, args.domain, pair_index=1)
    ]
    first_speedup = float(measurements[0]["speedup"])
    if first_speedup < SPEEDUP_FLOOR:
        measurements.append(
            _measure_pair(production_db, config, base, args.domain, pair_index=2)
        )
        measurements.append(
            _measure_pair(production_db, config, base, args.domain, pair_index=3)
        )

    speedups = [float(row["speedup"]) for row in measurements]
    decision_speedup = speedups[0] if len(speedups) == 1 else float(median(speedups))
    passed = decision_speedup >= SPEEDUP_FLOOR
    result = {
        "schema": "mdstats.qualification.mvsel2-harden1-v3.q7.materiality.v2",
        "production_database": str(production_db),
        "config": str(config),
        "domain": args.domain,
        "copy_only_snapshots": True,
        "fresh_pair_count": len(measurements),
        "measurements": measurements,
        "decision_rule": (
            "one valid pair when first speedup >= 10; otherwise median of three "
            "valid fresh pairs"
        ),
        "decision_speedup": decision_speedup,
        "required_speedup_floor": SPEEDUP_FLOOR,
        "passes_speedup_floor": passed,
        "resource_context": resource_context,
        "stage_resource_scope": (
            "candidate campaign orchestration wrappers; same process environment "
            "and production config for all fresh pairs"
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return 0 if passed else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    q6 = sub.add_parser("q6-prepare")
    q6.add_argument("--production-db", required=True)
    q6.add_argument("--domain", required=True)
    q6.add_argument("--config", required=True)
    q6.add_argument("--clone-root", required=True)
    q6.add_argument("--output", required=True)

    q7 = sub.add_parser("q7")
    q7.add_argument("--production-db", required=True)
    q7.add_argument("--domain", required=True)
    q7.add_argument("--config", required=True)
    q7.add_argument("--clone-root", required=True)
    q7.add_argument("--output", required=True)

    args = parser.parse_args()
    if args.command == "q6-prepare":
        return run_q6_prepare(args)
    return run_q7(args)


if __name__ == "__main__":
    raise SystemExit(main())
