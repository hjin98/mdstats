#!/usr/bin/env python3
"""Material qualification harness for MVSEL2 corrupt-newest recovery.

The production campaign is read only. The complete .mdstats directory is copied
into qualification scratch before any mutation. The recovery oracle is
established before fault injection by restoring the newest checkpoint and then
the highest older compatible checkpoint from the fresh uninterrupted run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import time

from mdstats.training_data import campaign_cli as cli
from mdstats.training_data import mvsel2_hardening_runtime as hardening
from mdstats.training_data.target_coverage import TargetCoverageReference
from mdstats.training_data.target_coverage_sparse_index import TargetCoverageSparseIndex
from mdstats.training_data.target_multi_view_selector_v2 import TargetMultiViewSelectorPolicyV2

EXPECTED_CANDIDATES = 36408
EXPECTED_FAMILIES = 165


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


def _restore_if_valid(
    *,
    pointer,
    size: int,
    store,
    reference_domain,
    forward_domain,
    dataset_id: str,
    policy: TargetMultiViewSelectorPolicyV2,
):
    try:
        state = hardening._restore_checkpoint(
            pointer,
            store=store,
            reference_domain=reference_domain,
            forward_domain=forward_domain,
            dataset_id=dataset_id,
            selector_policy=policy,
        )
    except Exception:
        return None
    return state if int(state.selected_count) == int(size) else None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--production-db", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--domain", required=True)
    p.add_argument("--clone-root", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    production_db = Path(args.production_db).expanduser().resolve()
    config = Path(args.config).expanduser().resolve()
    if not production_db.is_file():
        raise RuntimeError(f"production database not found: {production_db}")
    if not config.is_file():
        raise RuntimeError(f"campaign configuration not found: {config}")

    cloned_db = _clone_internal(production_db, Path(args.clone_root))
    cfg, _ = cli._load_config(config)
    store = cli.CampaignStore(cloned_db)
    try:
        reference = store.get_record(
            "target_coverage_reference", TargetCoverageReference
        )
        sparse = store.get_record(
            "target_coverage_sparse_index", TargetCoverageSparseIndex
        )
        forward = hardening._native_forward_view(store, sparse)
        reference_domain = reference.domain(args.domain)
        forward_domain = forward.domain(args.domain)
        if forward_domain.candidate_count != EXPECTED_CANDIDATES:
            raise RuntimeError(
                f"candidate-count mismatch: {forward_domain.candidate_count}"
            )
        if len(forward_domain.families) != EXPECTED_FAMILIES:
            raise RuntimeError(
                f"family-count mismatch: {len(forward_domain.families)}"
            )

        _delete_v2_authority(store)
        t0 = time.perf_counter()
        uninterrupted, checkpoints = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        uninterrupted_seconds = time.perf_counter() - t0

        policy = TargetMultiViewSelectorPolicyV2()
        rows = hardening._checkpoint_rows(store, args.domain)
        if len(rows) < 2:
            raise RuntimeError(
                f"need at least two MVSTATE2 checkpoints, found {len(rows)}"
            )

        newest_size, newest_pointer = rows[0]
        newest_state = _restore_if_valid(
            pointer=newest_pointer,
            size=newest_size,
            store=store,
            reference_domain=reference_domain,
            forward_domain=forward_domain,
            dataset_id=reference.dataset_id,
            policy=policy,
        )
        if newest_state is None:
            raise RuntimeError(
                "fresh uninterrupted run produced an unusable newest MVSTATE2 checkpoint"
            )

        fallback_size = None
        fallback_pointer = None
        for size, pointer in rows[1:]:
            state = _restore_if_valid(
                pointer=pointer,
                size=size,
                store=store,
                reference_domain=reference_domain,
                forward_domain=forward_domain,
                dataset_id=reference.dataset_id,
                policy=policy,
            )
            if state is not None:
                fallback_size = int(size)
                fallback_pointer = dict(pointer)
                break
        if fallback_size is None or fallback_pointer is None:
            raise RuntimeError(
                "no older valid compatible MVSTATE2 checkpoint exists for fallback"
            )

        corrupted_key = (
            f"target_multi_view_selection_state_v2:{args.domain}:{int(newest_size)}"
        )
        fallback_key = (
            f"target_multi_view_selection_state_v2:{args.domain}:{fallback_size}"
        )

        db = store._connect()
        db.execute("DELETE FROM records WHERE key='target_multi_view_selection_v2'")
        cursor = db.execute("UPDATE records SET payload='{}' WHERE key=?", (corrupted_key,))
        if cursor.rowcount != 1:
            raise RuntimeError(
                f"fault injection did not update exactly one expected checkpoint: {corrupted_key}"
            )
        db.commit()

        t1 = time.perf_counter()
        resumed, resumed_pointers = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        resumed_seconds = time.perf_counter() - t1

        resume_key = f"resume:{args.domain}"
        actual_resume_pointer = resumed_pointers.get(resume_key)
        if actual_resume_pointer is None:
            raise RuntimeError(
                "runtime did not report an MVSTATE2 resume pointer; "
                "cold rebuild is not acceptable recovery evidence"
            )
        if dict(actual_resume_pointer) != fallback_pointer:
            raise RuntimeError(
                "runtime did not resume from the prevalidated highest older compatible checkpoint: "
                f"expected={fallback_key} actual={actual_resume_pointer}"
            )
        if resumed.content_digest != uninterrupted.content_digest:
            raise RuntimeError(
                "resumed selector differs from uninterrupted selector: "
                f"{resumed.content_digest} != {uninterrupted.content_digest}"
            )

        result = {
            "schema": "mdstats.qualification.mvsel2-harden1-v3.q5.materiality.v2",
            "production_database": str(production_db),
            "ephemeral_database": str(cloned_db),
            "config": str(config),
            "domain": args.domain,
            "candidate_count": forward_domain.candidate_count,
            "family_count": len(forward_domain.families),
            "native_forward_runtime": True,
            "copy_only_snapshot": True,
            "newest_checkpoint_prevalidated": True,
            "corrupted_checkpoint_key": corrupted_key,
            "corrupted_checkpoint_size": int(newest_size),
            "expected_fallback_checkpoint_key": fallback_key,
            "expected_fallback_checkpoint_size": fallback_size,
            "expected_fallback_prevalidated": True,
            "actual_resume_pointer_matches_expected_fallback": True,
            "uninterrupted_selection_digest": uninterrupted.content_digest,
            "resumed_selection_digest": resumed.content_digest,
            "digest_equal": True,
            "generated_checkpoint_count": len(checkpoints),
            "uninterrupted_wall_seconds": uninterrupted_seconds,
            "resumed_wall_seconds": resumed_seconds,
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


if __name__ == "__main__":
    raise SystemExit(main())
