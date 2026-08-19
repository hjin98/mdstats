#!/usr/bin/env python3
"""Resource-bounded standalone qualification for the production MVSEL2 chain.

This driver is intentionally independent of Codex/ChatGPT session lifetime.  It
uses the production campaign as read-only authority, never clones the complete
``.mdstats`` tree, supervises expensive workers from a parent process, and
fails closed on RAM, scratch-disk, or wall-clock limits.

The production-scale checks are deliberately split by material purpose:

* Q5 copies only the small MVSTATE2 checkpoint bundles required to inject a
  corrupt-newest fault, resumes from the highest remaining compatible state,
  and compares against the already-authenticated production selection digest.
* Q6 invokes the existing read-only production REPAIR2 benchmark directly on
  the production database; no campaign snapshot is created.
* Q7 reuses the already-recorded same-production MVIDX performance projection
  only after binding it to the current production MVIDX content digest.  The
  historical projection is conservative and avoids an hours-to-days MVSEL1
  replay whose only purpose would be to re-establish an already-large margin.

All mutable files live below ``--root``.  The parent watchdog checks current
RSS, physical scratch blocks, and elapsed wall time and terminates a runaway
worker before the configured ceilings are exceeded for a sustained interval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from typing import Any, Mapping

GIB = 1024 ** 3
DEFAULT_DOMAIN = "label-domain-5aa1ee5d50cd0b23"
DEFAULT_CANDIDATES = 36_408
DEFAULT_FAMILIES = 165
DEFAULT_MEM_GIB = 48.0
DEFAULT_SCRATCH_GIB = 8.0
DEFAULT_Q5_SECONDS = 90 * 60
DEFAULT_Q6_SECONDS = 90 * 60
DEFAULT_TOTAL_SECONDS = 3 * 60 * 60
WATCH_INTERVAL_SECONDS = 2.0
LIMIT_GRACE_SAMPLES = 2


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _production_identity(database: Path, config: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "database": str(database),
        "database_sha256": _sha256(database),
        "database_size_bytes": database.stat().st_size,
    }
    if config is not None:
        result.update(
            config=str(config),
            config_sha256=_sha256(config),
            config_size_bytes=config.stat().st_size,
        )
    return result


def _pointer_ro(database: Path, key: str) -> dict[str, Any]:
    uri = f"file:{database.resolve()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        row = connection.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
    if row is None:
        raise RuntimeError(f"missing production campaign record: {key}")
    payload = json.loads(str(row[0]))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid production campaign record: {key}")
    return payload


def _checkpoint_rows_ro(database: Path, domain: str) -> list[tuple[int, dict[str, Any]]]:
    prefix = f"target_multi_view_selection_state_v2:{domain}:"
    uri = f"file:{database.resolve()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        rows = connection.execute(
            "SELECT key,payload FROM records WHERE key LIKE ?", (prefix + "%",)
        ).fetchall()
    result: list[tuple[int, dict[str, Any]]] = []
    for key, encoded in rows:
        try:
            size = int(str(key).rsplit(":", 1)[1])
            payload = json.loads(str(encoded))
        except Exception:
            continue
        if isinstance(payload, dict):
            result.append((size, payload))
    return sorted(result, key=lambda item: item[0], reverse=True)


def _rss_bytes(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _physical_tree_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    seen: set[tuple[int, int]] = set()
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(base) / name
            try:
                stat = path.lstat()
            except OSError:
                continue
            identity = (int(stat.st_dev), int(stat.st_ino))
            if identity in seen:
                continue
            seen.add(identity)
            total += int(getattr(stat, "st_blocks", 0)) * 512
    return total


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        process.terminate()
    deadline = time.monotonic() + 10.0
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.2)
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()


def _run_bounded(
    *,
    name: str,
    command: list[str],
    cwd: Path,
    log_path: Path,
    scratch_root: Path,
    max_rss_bytes: int,
    max_scratch_bytes: int,
    max_seconds: float,
) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    peak_rss = 0
    peak_scratch = 0
    rss_over = 0
    disk_over = 0
    reason: str | None = None
    env = os.environ.copy()
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("NUMEXPR_NUM_THREADS", "1")
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        while process.poll() is None:
            now = time.monotonic()
            rss = _rss_bytes(process.pid)
            scratch = _physical_tree_bytes(scratch_root)
            if rss is not None:
                peak_rss = max(peak_rss, rss)
                rss_over = rss_over + 1 if rss > max_rss_bytes else 0
            peak_scratch = max(peak_scratch, scratch)
            disk_over = disk_over + 1 if scratch > max_scratch_bytes else 0
            if rss_over >= LIMIT_GRACE_SAMPLES:
                reason = f"RSS_LIMIT_EXCEEDED:{rss}>{max_rss_bytes}"
            elif disk_over >= LIMIT_GRACE_SAMPLES:
                reason = f"SCRATCH_LIMIT_EXCEEDED:{scratch}>{max_scratch_bytes}"
            elif now - started > max_seconds:
                reason = f"TIME_LIMIT_EXCEEDED:{now-started:.1f}>{max_seconds:.1f}"
            if reason is not None:
                _terminate(process)
                break
            time.sleep(WATCH_INTERVAL_SECONDS)
        returncode = process.wait()
    elapsed = time.monotonic() - started
    status = "PASS" if returncode == 0 and reason is None else "FAIL"
    return {
        "stage": name,
        "status": status,
        "returncode": returncode,
        "limit_reason": reason,
        "wall_seconds": elapsed,
        "peak_worker_rss_bytes": peak_rss,
        "peak_scratch_physical_bytes": peak_scratch,
        "max_rss_bytes": max_rss_bytes,
        "max_scratch_bytes": max_scratch_bytes,
        "max_seconds": max_seconds,
        "command": command,
        "log": str(log_path),
    }


def _copy_checkpoint_bundle(
    pointer: Mapping[str, Any], production_root: Path, scratch_root: Path
) -> None:
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise RuntimeError("invalid MVSTATE2 pointer path")
    source_manifest = (production_root / relative).resolve()
    if production_root.resolve() not in source_manifest.parents or not source_manifest.is_file():
        raise RuntimeError(f"missing production MVSTATE2 manifest: {source_manifest}")
    source_dir = source_manifest.parent
    target_dir = scratch_root / relative.parent
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir, copy_function=shutil.copy2)


def _worker_q5(args: argparse.Namespace) -> int:
    import mdstats
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data import mvsel2_hardening_runtime as hardening
    from mdstats.training_data.target_coverage_sparse_index_store import (
        read_target_coverage_sparse_index_forward_view_native_record,
    )
    from mdstats.training_data.target_coverage_store import read_target_coverage_native_record
    from mdstats.training_data.target_multi_view_selector_v2_resume import (
        build_target_multi_view_selection_plan_v2_resumable,
    )

    database = Path(args.production_db).resolve()
    production_root = database.parent
    scratch = Path(args.stage_scratch).resolve()
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    reference = read_target_coverage_native_record(
        _pointer_ro(database, "target_coverage_reference"), production_root
    )
    sparse_pointer = _pointer_ro(database, "target_coverage_sparse_index")
    forward = read_target_coverage_sparse_index_forward_view_native_record(
        sparse_pointer, production_root
    )
    forward_domain = forward.domain(args.domain)
    if forward_domain.candidate_count != args.expected_candidates:
        raise RuntimeError("production candidate count mismatch")
    if len(forward_domain.families) != args.expected_families:
        raise RuntimeError("production family count mismatch")

    production_store = CampaignStore(database)
    try:
        selection = production_store.get_record_optional(
            "target_multi_view_selection_v2", mdstats.TargetMultiViewSelectionPlanV2
        )
        if selection is None:
            raise RuntimeError("production target_multi_view_selection_v2 is missing")
    finally:
        production_store.close()

    rows = [row for row in _checkpoint_rows_ro(database, args.domain) if row[0] <= 16384]
    if len(rows) < 2:
        raise RuntimeError("Q5 requires at least two production MVSTATE2 checkpoints")

    scratch_db = scratch / "qualification.sqlite3"
    scratch_store = CampaignStore(scratch_db)
    try:
        for size, pointer in rows:
            _copy_checkpoint_bundle(pointer, production_root, scratch)
            key = f"target_multi_view_selection_state_v2:{args.domain}:{size}"
            scratch_store.put_record(key, pointer)

        reference_domain = reference.domain(args.domain)
        policy = selection.policy
        newest_size, newest_pointer = rows[0]
        newest_state = hardening._restore_checkpoint(
            newest_pointer,
            store=scratch_store,
            reference_domain=reference_domain,
            forward_domain=forward_domain,
            dataset_id=reference.dataset_id,
            selector_policy=policy,
        )
        if int(newest_state.selected_count) != int(newest_size):
            raise RuntimeError("newest MVSTATE2 checkpoint is not self-consistent")

        fallback_size = None
        fallback_pointer: Mapping[str, Any] | None = None
        for size, pointer in rows[1:]:
            try:
                state = hardening._restore_checkpoint(
                    pointer,
                    store=scratch_store,
                    reference_domain=reference_domain,
                    forward_domain=forward_domain,
                    dataset_id=reference.dataset_id,
                    selector_policy=policy,
                )
            except Exception:
                continue
            if int(state.selected_count) == int(size):
                fallback_size = int(size)
                fallback_pointer = pointer
                break
        if fallback_size is None or fallback_pointer is None:
            raise RuntimeError("no older compatible MVSTATE2 checkpoint is available")

        newest_key = f"target_multi_view_selection_state_v2:{args.domain}:{newest_size}"
        db = scratch_store._connect()
        db.execute("UPDATE records SET payload='{}' WHERE key=?", (newest_key,))
        db.commit()

        resume_states, resume_pointers = hardening._highest_valid_resume_states(
            scratch_store, reference, forward, policy
        )
        actual = resume_pointers.get(args.domain)
        if actual is None or dict(actual) != dict(fallback_pointer):
            raise RuntimeError(
                "runtime did not choose the prevalidated highest older compatible checkpoint"
            )
        started = time.perf_counter()
        resumed = build_target_multi_view_selection_plan_v2_resumable(
            reference,
            forward,
            policy=policy,
            workers=1,
            resume_states=resume_states,
            progress_callback=lambda message: print(f"[Q5] {message}", flush=True),
            progress_interval_seconds=30.0,
        )
        elapsed = time.perf_counter() - started
        if resumed.content_digest != selection.content_digest:
            raise RuntimeError(
                "resumed selection digest differs from authenticated production authority"
            )
        payload = {
            "schema": "mdstats.mvsel2-bounded-qualification.q5.v1",
            "production_database": str(database),
            "domain": args.domain,
            "candidate_count": forward_domain.candidate_count,
            "family_count": len(forward_domain.families),
            "mvidx1_content_digest": forward.mvidx1_content_digest,
            "canonical_selection_digest": selection.content_digest,
            "resumed_selection_digest": resumed.content_digest,
            "newest_corrupted_size": int(newest_size),
            "highest_valid_fallback_size": int(fallback_size),
            "fallback_pointer_match": True,
            "digest_equal": True,
            "resume_wall_seconds": elapsed,
            "full_production_tree_copied": False,
            "copied_checkpoint_count": len(rows),
            "inverse_arrays_mapped_by_reader": False,
        }
        output = Path(args.worker_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
        return 0
    finally:
        scratch_store.close()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _validate_q7_projection(database: Path, benchmark: Path) -> dict[str, Any]:
    pointer = _pointer_ro(database, "target_coverage_sparse_index")
    current_digest = str(pointer.get("content_digest", ""))
    evidence = _load_json(benchmark)
    source_input = evidence.get("input", {})
    projection = evidence.get("projection", {})
    if not isinstance(source_input, Mapping) or not isinstance(projection, Mapping):
        raise RuntimeError("production performance benchmark lacks required input/projection fields")
    if str(source_input.get("mvidx1_content_digest")) != current_digest:
        raise RuntimeError("historical performance evidence is for a different MVIDX1 graph")
    if int(source_input.get("candidate_count", -1)) != DEFAULT_CANDIDATES:
        raise RuntimeError("historical performance evidence candidate count mismatch")
    if int(source_input.get("family_count", -1)) != DEFAULT_FAMILIES:
        raise RuntimeError("historical performance evidence family count mismatch")
    speedup = float(projection.get("projected_speedup", 0.0))
    passed = bool(projection.get("minimum_10x_pass", False)) and speedup >= 10.0
    return {
        "schema": "mdstats.mvsel2-bounded-qualification.q7-reuse.v1",
        "evidence": str(benchmark),
        "mvidx1_content_digest": current_digest,
        "baseline_full_order_seconds": float(projection.get("baseline_full_order_seconds")),
        "mvsel2_full_order_seconds": float(projection.get("mvsel2_full_order_seconds")),
        "projected_speedup": speedup,
        "minimum_10x_pass": passed,
        "method": str(projection.get("method", "")),
        "rerun_policy": "reuse_same-production conservative projection; no unbounded MVSEL1 replay",
    }


def _write_state(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _main_supervisor(args: argparse.Namespace) -> int:
    repo = Path.cwd().resolve()
    database = Path(args.production_db).expanduser().resolve()
    config = Path(args.config).expanduser().resolve() if args.config else None
    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not database.is_file():
        raise RuntimeError(f"production database not found: {database}")
    if config is not None and not config.is_file():
        raise RuntimeError(f"campaign config not found: {config}")
    if root == database.parent or database.parent in root.parents:
        raise RuntimeError("qualification root must be outside production .mdstats")

    max_rss = int(args.max_rss_gib * GIB)
    max_scratch = int(args.max_scratch_gib * GIB)
    if max_rss <= 0 or max_scratch <= 0:
        raise RuntimeError("resource limits must be positive")
    free_disk = shutil.disk_usage(root).free
    if free_disk < max_scratch + 2 * GIB:
        raise RuntimeError(
            f"insufficient free disk for bounded qualification: free={free_disk} "
            f"required_headroom={max_scratch + 2 * GIB}"
        )

    identity_before = _production_identity(database, config)
    state_path = root / "state.json"
    prior = _load_json(state_path) if state_path.is_file() else {}
    if prior.get("production_identity") not in (None, identity_before):
        raise RuntimeError("production input identity changed since prior qualification attempt")
    state: dict[str, Any] = {
        "schema": "mdstats.mvsel2-bounded-qualification.state.v1",
        "production_identity": identity_before,
        "limits": {
            "max_rss_gib": args.max_rss_gib,
            "max_scratch_gib": args.max_scratch_gib,
            "q5_timeout_seconds": args.q5_timeout_seconds,
            "q6_timeout_seconds": args.q6_timeout_seconds,
            "total_timeout_seconds": args.total_timeout_seconds,
        },
        "stages": dict(prior.get("stages", {})) if isinstance(prior.get("stages"), dict) else {},
    }
    _write_state(state_path, state)
    total_started = time.monotonic()

    def remaining() -> float:
        return args.total_timeout_seconds - (time.monotonic() - total_started)

    q5_output = root / "q5_recovery.json"
    q5_scratch = root / "q5-scratch"
    if state["stages"].get("q5", {}).get("status") != "PASS":
        timeout = min(float(args.q5_timeout_seconds), remaining())
        if timeout <= 0:
            raise RuntimeError("total qualification time budget exhausted before Q5")
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-q5",
            "--production-db", str(database),
            "--domain", args.domain,
            "--expected-candidates", str(args.expected_candidates),
            "--expected-families", str(args.expected_families),
            "--stage-scratch", str(q5_scratch),
            "--worker-output", str(q5_output),
        ]
        result = _run_bounded(
            name="q5",
            command=cmd,
            cwd=repo,
            log_path=root / "q5_recovery.log",
            scratch_root=root,
            max_rss_bytes=max_rss,
            max_scratch_bytes=max_scratch,
            max_seconds=timeout,
        )
        state["stages"]["q5"] = result
        _write_state(state_path, state)
        if result["status"] != "PASS":
            print(json.dumps(result, indent=2, sort_keys=True), flush=True)
            return 2
        shutil.rmtree(q5_scratch, ignore_errors=True)

    identity_after_q5 = _production_identity(database, config)
    if identity_after_q5 != identity_before:
        raise RuntimeError("production input changed during Q5; result invalidated")

    q6_output = root / "q6_repair2_production.json"
    if state["stages"].get("q6", {}).get("status") != "PASS":
        timeout = min(float(args.q6_timeout_seconds), remaining())
        if timeout <= 0:
            raise RuntimeError("total qualification time budget exhausted before Q6")
        benchmark = repo / "benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py"
        cmd = [
            sys.executable,
            str(benchmark),
            str(database),
            "--domain", args.domain,
            "--workplan-id", "DOC-MVSEL2-HARDEN1-V3",
            "--workplan-revision", "5",
            "--workplan-sha256", "resource-bounded-standalone-qualification",
            "--expected-candidate-count", str(args.expected_candidates),
            "--expected-family-count", str(args.expected_families),
            "--output", str(q6_output),
        ]
        result = _run_bounded(
            name="q6",
            command=cmd,
            cwd=repo,
            log_path=root / "q6_repair2_production.log",
            scratch_root=root,
            max_rss_bytes=max_rss,
            max_scratch_bytes=max_scratch,
            max_seconds=timeout,
        )
        state["stages"]["q6"] = result
        _write_state(state_path, state)
        if result["status"] != "PASS":
            print(json.dumps(result, indent=2, sort_keys=True), flush=True)
            return 3

    identity_after_q6 = _production_identity(database, config)
    if identity_after_q6 != identity_before:
        raise RuntimeError("production input changed during Q6; result invalidated")

    if state["stages"].get("q7", {}).get("status") != "PASS":
        q7 = _validate_q7_projection(
            database, repo / "benchmarks/mlff_mvsel2_production_density_2026-08-18.json"
        )
        q7_path = root / "q7_performance_reuse.json"
        q7_path.write_text(json.dumps(q7, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        state["stages"]["q7"] = {
            "stage": "q7",
            "status": "PASS" if q7["minimum_10x_pass"] else "FAIL",
            "evidence": str(q7_path),
            "projected_speedup": q7["projected_speedup"],
        }
        _write_state(state_path, state)
        if not q7["minimum_10x_pass"]:
            return 4

    identity_final = _production_identity(database, config)
    if identity_final != identity_before:
        raise RuntimeError("production input changed during qualification; results invalidated")

    summary = {
        "schema": "mdstats.mvsel2-bounded-qualification.summary.v1",
        "status": "PASS",
        "production_identity": identity_before,
        "limits": state["limits"],
        "stages": state["stages"],
        "scratch_physical_bytes_final": _physical_tree_bytes(root),
        "codex_required": False,
        "full_mdstats_snapshot_created": False,
        "production_mutation": False,
    }
    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-db")
    parser.add_argument("--config")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--root", default="qualification/bounded-mvsel2")
    parser.add_argument("--expected-candidates", type=int, default=DEFAULT_CANDIDATES)
    parser.add_argument("--expected-families", type=int, default=DEFAULT_FAMILIES)
    parser.add_argument("--max-rss-gib", type=float, default=DEFAULT_MEM_GIB)
    parser.add_argument("--max-scratch-gib", type=float, default=DEFAULT_SCRATCH_GIB)
    parser.add_argument("--q5-timeout-seconds", type=float, default=DEFAULT_Q5_SECONDS)
    parser.add_argument("--q6-timeout-seconds", type=float, default=DEFAULT_Q6_SECONDS)
    parser.add_argument("--total-timeout-seconds", type=float, default=DEFAULT_TOTAL_SECONDS)
    parser.add_argument("--worker-q5", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--stage-scratch", help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.production_db:
        raise SystemExit("--production-db is required")
    if args.worker_q5:
        if not args.stage_scratch or not args.worker_output:
            raise SystemExit("worker Q5 requires --stage-scratch and --worker-output")
        return _worker_q5(args)
    return _main_supervisor(args)


if __name__ == "__main__":
    raise SystemExit(main())
