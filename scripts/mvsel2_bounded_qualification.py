#!/usr/bin/env python3
"""Visible fail-safe entrypoint for the REV8 bounded MVSEL2 qualifier.

The heavy qualification implementation is kept byte-for-byte in
``mvsel2_bounded_qualification_core.py``.  This entrypoint is qualification-only:
it adds visible progress and guarantees a compact terminal capsule if the core
qualifier exits before publishing normal evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

DEFAULT_ROOT = Path("qualification/bounded-mvsel2")
POLL_SECONDS = 15.0
EMERGENCY_SCHEMA = "mdstats.mvsel2-qualification-runner-emergency.v1"


def _json_load(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _root_from_args(arguments: list[str]) -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    known, _unknown = parser.parse_known_args(arguments)
    return Path(known.root).expanduser().resolve()


def _latest_evidence(root: Path, *, newer_than_ns: int | None = None) -> Path | None:
    parent = root / "evidence"
    if not parent.is_dir():
        return None
    runs = []
    for path in parent.iterdir():
        if not path.is_dir():
            continue
        try:
            modified = path.stat().st_mtime_ns
        except OSError:
            continue
        if newer_than_ns is not None and modified < newer_than_ns:
            continue
        runs.append((modified, path))
    runs.sort(reverse=True)
    return runs[0][1] if runs else None


def _tail(path: Path, limit: int = 4000) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return data[-limit:].decode("utf-8", errors="replace")


def _emergency_summary(
    *,
    root: Path,
    returncode: int,
    command: list[str],
    elapsed_seconds: float,
    run_started_ns: int,
) -> Path:
    latest = _latest_evidence(root, newer_than_ns=run_started_ns)
    log_tail = ""
    worker = None
    if latest is not None:
        log_tail = _tail(latest / "worker.log")
        worker = _json_load(latest / "worker.json")

    run_id = datetime.now(timezone.utc).strftime("emergency-%Y%m%dT%H%M%SZ")
    evidence = root / "evidence" / run_id
    payload: dict[str, Any] = {
        "schema": EMERGENCY_SCHEMA,
        "run_id": run_id,
        "status": "BLOCKED",
        "classification": "QUALIFIER_EXITED_WITHOUT_TERMINAL_EVIDENCE",
        "returncode": int(returncode),
        "elapsed_seconds": float(elapsed_seconds),
        "cwd": str(Path.cwd().resolve()),
        "command": command,
        "current_run_evidence": None if latest is None else str(latest),
        "current_run_worker_evidence": worker,
        "current_run_worker_log_tail": log_tail,
        "codex_required": False,
        "product_failure": False,
    }
    summary = evidence / "summary.json"
    _json_dump(summary, payload)
    _json_dump(root / "summary.json", payload)
    _json_dump(
        root / "state.json",
        {
            "schema": EMERGENCY_SCHEMA,
            "run_id": run_id,
            "status": "BLOCKED",
            "classification": payload["classification"],
            "summary": str(summary),
        },
    )
    return summary


def main() -> int:
    arguments = sys.argv[1:]
    root = _root_from_args(arguments)
    root.mkdir(parents=True, exist_ok=True)
    core = Path(__file__).with_name("mvsel2_bounded_qualification_core.py").resolve()
    if not core.is_file():
        raise SystemExit(f"bounded qualifier core not found: {core}")

    # Root summary/state are only convenience pointers.  Historical compact
    # evidence stays in evidence/<run-id>; removing these prevents a failed new
    # launch from being mistaken for the previous run's terminal result.
    (root / "summary.json").unlink(missing_ok=True)
    (root / "state.json").unlink(missing_ok=True)

    command = [sys.executable, str(core), *arguments]
    run_started_ns = time.time_ns()
    print(f"[REV8 runner] root={root}", flush=True)
    print(f"[REV8 runner] core={core}", flush=True)

    started = time.monotonic()
    try:
        process = subprocess.Popen(command, cwd=Path.cwd())
    except Exception as exc:
        summary_path = _emergency_summary(
            root=root,
            returncode=127,
            command=command,
            elapsed_seconds=time.monotonic() - started,
            run_started_ns=run_started_ns,
        )
        print(
            f"[REV8 qualification] FINAL status=BLOCKED; "
            f"classification=QUALIFIER_LAUNCH_FAILED; error={type(exc).__name__}: {exc}",
            flush=True,
        )
        print(f"[REV8 qualification] summary={summary_path}", flush=True)
        return 3

    last_status: tuple[str, str] | None = None
    last_report = 0.0
    while process.poll() is None:
        now = time.monotonic()
        state = _json_load(root / "state.json")
        status = "STARTING" if state is None else str(state.get("status", "RUNNING"))
        classification = "" if state is None else str(state.get("classification", ""))
        current = (status, classification)
        if current != last_status or now - last_report >= POLL_SECONDS:
            latest = _latest_evidence(root, newer_than_ns=run_started_ns)
            latest_text = "--" if latest is None else latest.name
            print(
                "[REV8 runner] "
                f"status={status}; elapsed={now - started:.0f}s; "
                f"evidence={latest_text}",
                flush=True,
            )
            last_status = current
            last_report = now
        time.sleep(1.0)

    returncode = int(process.wait())
    elapsed = time.monotonic() - started
    summary_path = root / "summary.json"
    summary = _json_load(summary_path)
    if summary is None:
        summary_path = _emergency_summary(
            root=root,
            returncode=returncode,
            command=command,
            elapsed_seconds=elapsed,
            run_started_ns=run_started_ns,
        )
        summary = _json_load(summary_path) or {}

    status = str(summary.get("status", "BLOCKED"))
    classification = str(summary.get("classification", "UNKNOWN"))
    evidence = _latest_evidence(root, newer_than_ns=run_started_ns)
    worker_path = None if evidence is None else evidence / "worker.json"
    worker = _json_load(worker_path) if worker_path is not None and worker_path.is_file() else None
    if worker is None:
        embedded = summary.get("worker_evidence")
        worker = embedded if isinstance(embedded, dict) else None

    worker_class = "" if worker is None else str(worker.get("failure_class", ""))
    worker_error = "" if worker is None else str(worker.get("error", ""))
    stage_class = ""
    stage_reason = ""
    if worker is not None and not worker_error:
        stages = worker.get("stages")
        if isinstance(stages, dict):
            for stage_name, stage in stages.items():
                if not isinstance(stage, dict):
                    continue
                stage_status = str(stage.get("status", ""))
                reason = str(stage.get("reason", ""))
                if stage_status in {"BLOCKED", "FAIL"}:
                    stage_class = f"{stage_name}_{stage_status}"
                    stage_reason = reason
                    break
    display_classification = worker_class or stage_class or classification
    display_reason = worker_error or stage_reason

    print(
        f"[REV8 qualification] FINAL status={status}; "
        f"classification={display_classification}; elapsed={elapsed:.1f}s; "
        f"returncode={returncode}",
        flush=True,
    )
    if display_reason:
        print(f"[REV8 qualification] reason={display_reason}", flush=True)
    if worker is not None and worker.get("selection_authority_source"):
        print(
            "[REV8 qualification] selection-authority="
            f"{worker['selection_authority_source']}",
            flush=True,
        )
    print(f"[REV8 qualification] summary={summary_path}", flush=True)
    print(f"[REV8 qualification] state={root / 'state.json'}", flush=True)
    if worker_path is not None and worker_path.is_file():
        print(f"[REV8 qualification] worker={worker_path}", flush=True)
    if evidence is not None and (evidence / "worker.log").is_file():
        print(f"[REV8 qualification] log={evidence / 'worker.log'}", flush=True)

    if status == "PASS":
        return 0
    if status == "FAIL":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
