#!/usr/bin/env python3
"""Cheap read-only persistence probe for REV8 MVSEL2 qualification.

This probe intentionally does not run G5, does not deserialize TARGET-DATA2B,
and does not map MVIDX1.  It inspects only SQLite record keys and the bounded
immutable MVSTATE2 bundle discovery used by the qualification wrapper.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any

import mvsel2_bounded_qualification_core as core

EXPECTED_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-db", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument(
        "--root",
        default="qualification/bounded-mvsel2",
        help="qualification evidence root used only for the compact probe JSON",
    )
    return parser.parse_args()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> int:
    args = _parse_args()
    database = Path(args.production_db).expanduser().resolve()
    root = Path(args.root).expanduser().resolve()
    output = root / "checkpoint-probe.json"
    if not database.is_file():
        raise SystemExit(f"production database not found: {database}")

    uri = f"file:{database}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        keys = tuple(
            str(row[0])
            for row in connection.execute(
                "SELECT key FROM records WHERE key LIKE '%multi_view%' ORDER BY key"
            ).fetchall()
        )
        final_plan_present = connection.execute(
            "SELECT 1 FROM records WHERE key=? LIMIT 1",
            ("target_multi_view_selection_v2",),
        ).fetchone() is not None
        db_rows = core.adapted._ORIGINAL_RECOVERY_ROWS_ALL(connection)
        db_sizes = tuple(sorted(int(v) for v in db_rows.get(args.domain, {})))

        scan_error = None
        try:
            merged = core.adapted._checkpoint_rows_all(connection)
        except Exception as exc:  # probe reports the condition rather than failing qualification
            merged = {}
            scan_error = f"{type(exc).__name__}: {exc}"
        merged_sizes = tuple(
            sorted(int(v) for v in merged.get(args.domain, {}))
        )
        discovery = core.adapted._DISCOVERY_REPORT or {}

        recovered_raw = discovery.get("recovered", {})
        recovered_domain = (
            recovered_raw.get(args.domain, {})
            if isinstance(recovered_raw, dict)
            else {}
        )
        recovered_sizes = tuple(
            sorted(int(v) for v in recovered_domain)
        ) if isinstance(recovered_domain, dict) else ()
        ambiguous = discovery.get("ambiguous", {})
        domain_ambiguous = (
            ambiguous.get(args.domain, {})
            if isinstance(ambiguous, dict)
            else {}
        )

        expected = tuple(EXPECTED_SIZES)
        missing = tuple(size for size in expected if size not in merged_sizes)
        if final_plan_present:
            conclusion = "FINAL_PLAN_PRESENT"
        elif domain_ambiguous:
            conclusion = "AMBIGUOUS_MVSTATE2_ARTIFACTS"
        elif not missing:
            conclusion = "CHECKPOINT_LADDER_AVAILABLE"
        elif merged_sizes:
            conclusion = "CHECKPOINT_LADDER_INCOMPLETE"
        else:
            conclusion = "NO_MVSTATE2_ARTIFACTS"

        payload: dict[str, Any] = {
            "schema": "mdstats.mvsel2-checkpoint-probe.v1",
            "production_database": str(database),
            "production_root": str(database.parent),
            "domain": str(args.domain),
            "final_plan_present": bool(final_plan_present),
            "matching_multi_view_record_keys": keys,
            "db_mvstate2_sizes": db_sizes,
            "merged_mvstate2_sizes": merged_sizes,
            "orphan_recovered_sizes": recovered_sizes,
            "expected_sizes": expected,
            "missing_sizes": missing,
            "bundle_manifests_found": int(discovery.get("bundle_manifests_found", 0) or 0),
            "directories_scanned": int(discovery.get("directories_scanned", 0) or 0),
            "rejected_manifests": int(discovery.get("rejected_manifests", 0) or 0),
            "ambiguous": domain_ambiguous,
            "scan_error": scan_error,
            "conclusion": conclusion,
            "mapped_target_data2b": False,
            "mapped_mvidx1": False,
            "g5_executed": False,
            "production_mutated": False,
        }
        _json_dump(output, payload)
    finally:
        connection.close()

    print(f"[REV8 probe] final-plan={'present' if final_plan_present else 'absent'}")
    print(f"[REV8 probe] db-mvstate2-sizes={list(db_sizes)}")
    print(
        "[REV8 probe] orphan-manifests="
        f"{payload['bundle_manifests_found']}; recovered-sizes={list(recovered_sizes)}"
    )
    if scan_error:
        print(f"[REV8 probe] scan-note={scan_error}")
    print(f"[REV8 probe] conclusion={conclusion}; missing={list(missing)}")
    print(f"[REV8 probe] report={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
