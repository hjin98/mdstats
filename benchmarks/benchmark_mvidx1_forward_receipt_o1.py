#!/usr/bin/env python3
"""Focused product meter for the O0 MVIDX1 forward-reopen optimization.

The benchmark requires an existing exact compound MVIDX1 validation receipt and
measures only the receipt-aware forward-only reopen used by MVSEL2/REPAIR2. It
never writes campaign scientific authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import sqlite3
import subprocess
import time

from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data import mvidx1_forward_receipt_runtime as runtime
from mdstats.training_data import target_coverage_sparse_index_store as native_store
from mdstats.training_data.progress_timing import format_progress_time


def _pointer(database: Path, key: str) -> dict[str, object]:
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        row = connection.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
    if row is None:
        raise RuntimeError(f"missing campaign record: {key}")
    payload = json.loads(row[0])
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid campaign record: {key}")
    return payload


def _usage() -> dict[str, float | int]:
    value = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "user_cpu_seconds": float(value.ru_utime),
        "system_cpu_seconds": float(value.ru_stime),
        "minor_faults": int(value.ru_minflt),
        "major_faults": int(value.ru_majflt),
        "filesystem_inputs": int(value.ru_inblock),
        "filesystem_outputs": int(value.ru_oublock),
        "peak_rss_kib": int(value.ru_maxrss),
    }


def _usage_delta(before: dict[str, float | int], after: dict[str, float | int]) -> dict[str, float | int]:
    return {
        "user_cpu_seconds": float(after["user_cpu_seconds"]) - float(before["user_cpu_seconds"]),
        "system_cpu_seconds": float(after["system_cpu_seconds"]) - float(before["system_cpu_seconds"]),
        "minor_faults": int(after["minor_faults"]) - int(before["minor_faults"]),
        "major_faults": int(after["major_faults"]) - int(before["major_faults"]),
        "filesystem_inputs": int(after["filesystem_inputs"]) - int(before["filesystem_inputs"]),
        "filesystem_outputs": int(after["filesystem_outputs"]) - int(before["filesystem_outputs"]),
        "peak_rss_kib": int(after["peak_rss_kib"]),
    }


def _proc_io() -> dict[str, int] | None:
    try:
        rows = {}
        for line in Path("/proc/self/io").read_text(encoding="utf-8").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                rows[key.strip()] = int(value.strip())
        return {
            "read_bytes": rows.get("read_bytes", 0),
            "write_bytes": rows.get("write_bytes", 0),
        }
    except (OSError, ValueError):
        return None


def _proc_io_delta(before: dict[str, int] | None, after: dict[str, int] | None) -> dict[str, int] | None:
    if before is None or after is None:
        return None
    return {key: after[key] - before[key] for key in ("read_bytes", "write_bytes")}


def _vm_kib(name: str) -> int | None:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_database", type=Path)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-candidate-count", type=int, default=36408)
    parser.add_argument("--expected-family-count", type=int, default=165)
    parser.add_argument("--expected-forward-edge-count", type=int, default=9505021522)
    args = parser.parse_args()

    database = args.campaign_database.resolve()
    state_root = database.parent
    pointer = _pointer(database, "target_coverage_sparse_index")

    campaign_store = CampaignStore(database)
    try:
        manifest_path, manifest = runtime._authenticated_manifest(pointer, state_root)
        restore_identity, logical_bytes = native_store._restore_identity(
            manifest_path.parent,
            manifest,
        )
        expected_digest = str(manifest["index_content_digest"])
        receipt_hit = (
            native_store.read_validation_receipt(
                native_store._MVIDX_VALIDATION_RECEIPT_NAMESPACE,
                restore_identity,
            )
            == expected_digest
        )
        if not receipt_hit:
            raise RuntimeError(
                "O1 forward-reopen meter requires an exact MVIDX1 compound validation receipt hit"
            )

        usage_before = _usage()
        io_before = _proc_io()
        rss_before = _vm_kib("VmRSS")
        swap_before = _vm_kib("VmSwap")
        started = time.perf_counter()
        forward = runtime.read_target_coverage_sparse_index_forward_view_native_record_receipt_aware(
            pointer,
            state_root,
        )
        wall = time.perf_counter() - started
        usage_after = _usage()
        io_after = _proc_io()
        rss_after = _vm_kib("VmRSS")
        swap_after = _vm_kib("VmSwap")
    finally:
        campaign_store.close()

    domain = forward.domain(args.domain)
    edge_count = int(sum(family.edge_count for family in domain.families))
    identity_ok = (
        forward.mvidx1_content_digest == expected_digest
        and domain.candidate_count == args.expected_candidate_count
        and len(domain.families) == args.expected_family_count
        and edge_count == args.expected_forward_edge_count
    )
    payload = {
        "schema": "mdstats.benchmark.mvidx1-forward-receipt-o1.v1",
        "source": {"git_head": _git_head()},
        "input": {
            "campaign_database": str(database),
            "domain": args.domain,
            "mvidx1_content_digest": expected_digest,
            "logical_native_bytes": logical_bytes,
            "candidate_count": domain.candidate_count,
            "family_count": len(domain.families),
            "forward_edge_count": edge_count,
        },
        "execution": {
            "compound_validation_receipt_hit": receipt_hit,
            "wall_seconds": wall,
            "wall_hhmmss": format_progress_time(wall),
            "resource_delta": _usage_delta(usage_before, usage_after),
            "proc_io_delta": _proc_io_delta(io_before, io_after),
            "rss_kib_before": rss_before,
            "rss_kib_after": rss_after,
            "swap_kib_before": swap_before,
            "swap_kib_after": swap_after,
        },
        "qualification": {
            "product_identity_match": identity_ok,
            "receipt_hit": receipt_hit,
            "scientific_authority_written": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    return 0 if identity_ok and receipt_hit else 2


if __name__ == "__main__":
    raise SystemExit(main())
