#!/usr/bin/env python3
"""Visible fail-safe runner for the REV8 bounded MVSEL2 qualifier.

This wrapper is qualification-only.  It does not change MVSEL2/MVSTATE2/REPAIR2
science or production execution.  It makes the existing autonomous qualifier
observable and guarantees a compact terminal capsule even if the underlying
supervisor exits before publishing its normal summary.
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


def _latest_evidence(root: Path) -> Path | None:
    parent = root / "evidence"
    if not parent.is_dir():
        return None
    runs = sorted(
        (path for path in parent.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    return runs[0] if runs else None


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
) -> Path:
    latest = _latest_evidence(root)
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
        "prior_latest_evidence": None if latest is None else str(latest),
        "prior_worker_evidence": worker,
        "prior_worker_log_tail": log_tail,
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
    qualifier = Path(__file__).with_name("mvsel2_bounded_qualification.py").resolve()
    if not qualifier.is_file():
        raise SystemExit(f"bounded qualifier not found: {qualifier}")

    command = [sys.executable, str(qualifier), *arguments]
    print(f"[REV8 runner] root={root}", flush=True)
    print(f"[REV8 runner] qualifier={qualifier}", flush=True)

    started = time.monotonic()
    process = subprocess.Popen(command, cwd=Path.cwd())
    last_status: tuple[str, str] | None = None
    last_report = 0.0

    while process.poll() is None:
        now = time.monotonic()
        state = _json_load(root / "state.json")
        status = "STARTING" if state is None else str(state.get("status", "RUNNING"))
        classification = "" if state is None else str(state.get("classification", ""))
        current = (status, classification)
        if current != last_status or now - last_report >= POLL_SECONDS:
            latest = _latest_evidence(root)
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
        )
        summary = _json_load(summary_path) or {}

    status = str(summary.get("status", "BLOCKED"))
    classification = str(summary.get("classification", "UNKNOWN"))
    evidence = _latest_evidence(root)
    worker = None if evidence is None else evidence / "worker.json"

    print(
        f"[REV8 qualification] FINAL status={status}; "
        f"classification={classification}; elapsed={elapsed:.1f}s; "
        f"returncode={returncode}",
        flush=True,
    )
    print(f"[REV8 qualification] summary={summary_path}", flush=True)
    print(f"[REV8 qualification] state={root / 'state.json'}", flush=True)
    if worker is not None and worker.is_file():
        print(f"[REV8 qualification] worker={worker}", flush=True)
    if evidence is not None and (evidence / "worker.log").is_file():
        print(f"[REV8 qualification] log={evidence / 'worker.log'}", flush=True)

    if status == "PASS":
        return 0
    if status == "FAIL":
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
