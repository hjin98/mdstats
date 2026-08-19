#!/usr/bin/env python3
"""Minimal material qualification for MVSEL2 corrupt-newest recovery."""
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
    if source.suffix in {'.sqlite', '.sqlite3', '.db'} or source.name.endswith(('-wal', '-shm')):
        return shutil.copy2(source, target)
    try:
        os.link(source, target)
        return str(target)
    except OSError:
        return shutil.copy2(source, target)


def _clone_internal(production_db: Path, root: Path) -> Path:
    source_internal = production_db.resolve().parent
    target_internal = root.resolve() / '.mdstats'
    if target_internal.exists():
        shutil.rmtree(target_internal)
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_internal, target_internal, copy_function=_copy_file)
    cloned_db = target_internal / production_db.name
    if not cloned_db.is_file():
        raise RuntimeError(f'cloned campaign database missing: {cloned_db}')
    return cloned_db


def _delete_v2_authority(store) -> None:
    db = store._connect()
    db.execute("DELETE FROM records WHERE key IN ('target_multi_view_selection_v2','target_multi_view_repair_v2')")
    db.execute("DELETE FROM records WHERE key LIKE 'target_multi_view_selection_state_v2:%'")
    db.commit()


def _payload(store, key: str):
    row = store._connect().execute('SELECT payload FROM records WHERE key=?', (key,)).fetchone()
    if row is None:
        raise RuntimeError(f'missing record: {key}')
    value = json.loads(str(row[0]))
    if not isinstance(value, dict):
        raise RuntimeError(f'invalid pointer payload: {key}')
    return value


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--production-db', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--domain', required=True)
    p.add_argument('--clone-root', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()

    production_db = Path(args.production_db).expanduser().resolve()
    config = Path(args.config).expanduser().resolve()
    if not production_db.is_file():
        raise RuntimeError(f'production database not found: {production_db}')
    if not config.is_file():
        raise RuntimeError(f'campaign configuration not found: {config}')

    cloned_db = _clone_internal(production_db, Path(args.clone_root))
    cfg, _ = cli._load_config(config)
    store = cli.CampaignStore(cloned_db)
    try:
        reference = store.get_record('target_coverage_reference', TargetCoverageReference)
        sparse = store.get_record('target_coverage_sparse_index', TargetCoverageSparseIndex)
        forward = hardening._native_forward_view(store, sparse)
        forward_domain = forward.domain(args.domain)
        if forward_domain.candidate_count != EXPECTED_CANDIDATES:
            raise RuntimeError(f'candidate-count mismatch: {forward_domain.candidate_count}')
        if len(forward_domain.families) != EXPECTED_FAMILIES:
            raise RuntimeError(f'family-count mismatch: {len(forward_domain.families)}')

        _delete_v2_authority(store)
        t0 = time.perf_counter()
        uninterrupted, checkpoints = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        uninterrupted_seconds = time.perf_counter() - t0

        rows = store._connect().execute(
            'SELECT key FROM records WHERE key LIKE ?',
            (f'target_multi_view_selection_state_v2:{args.domain}:%',),
        ).fetchall()
        domain_rows: list[tuple[int, str]] = []
        for (key,) in rows:
            try:
                size = int(str(key).rsplit(':', 1)[1])
            except Exception:
                continue
            domain_rows.append((size, str(key)))
        domain_rows.sort(reverse=True)
        if len(domain_rows) < 2:
            raise RuntimeError(f'need at least two MVSTATE2 checkpoints, found {domain_rows}')

        corrupted_size, corrupted_key = domain_rows[0]
        fallback_size, fallback_key = domain_rows[1]
        expected_fallback_pointer = _payload(store, fallback_key)

        db = store._connect()
        db.execute("DELETE FROM records WHERE key='target_multi_view_selection_v2'")
        db.execute("UPDATE records SET payload='{}' WHERE key=?", (corrupted_key,))
        db.commit()

        t1 = time.perf_counter()
        resumed, resumed_pointers = cli._ensure_target_multi_view_selection_v2(
            store, cfg=cfg, coverage_reference=reference, sparse_index=sparse
        )
        resumed_seconds = time.perf_counter() - t1

        resume_key = f'resume:{args.domain}'
        actual_resume_pointer = resumed_pointers.get(resume_key)
        if actual_resume_pointer is None:
            raise RuntimeError('runtime did not report an MVSTATE2 resume pointer; cold rebuild is not acceptable evidence')
        if dict(actual_resume_pointer) != expected_fallback_pointer:
            raise RuntimeError(
                'runtime did not resume from the immediately preceding valid checkpoint: '
                f'expected={fallback_key} actual={actual_resume_pointer}'
            )
        if resumed.content_digest != uninterrupted.content_digest:
            raise RuntimeError(
                'resumed selector differs from uninterrupted selector: '
                f'{resumed.content_digest} != {uninterrupted.content_digest}'
            )

        result = {
            'production_database': str(production_db),
            'ephemeral_database': str(cloned_db),
            'config': str(config),
            'domain': args.domain,
            'candidate_count': forward_domain.candidate_count,
            'family_count': len(forward_domain.families),
            'native_forward_runtime': True,
            'corrupted_checkpoint_key': corrupted_key,
            'corrupted_checkpoint_size': corrupted_size,
            'expected_fallback_checkpoint_key': fallback_key,
            'expected_fallback_checkpoint_size': fallback_size,
            'actual_resume_pointer_matches_expected_fallback': True,
            'uninterrupted_selection_digest': uninterrupted.content_digest,
            'resumed_selection_digest': resumed.content_digest,
            'digest_equal': True,
            'generated_checkpoint_count': len(checkpoints),
            'uninterrupted_wall_seconds': uninterrupted_seconds,
            'resumed_wall_seconds': resumed_seconds,
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        return 0
    finally:
        store.close()


if __name__ == '__main__':
    raise SystemExit(main())
