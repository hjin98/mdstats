#!/usr/bin/env python3
"""Observation-only O0 meter for the unchanged MLFF campaign ``prepare`` path.

The wrapper launches an arbitrary command after ``--``, tees combined stdout/stderr,
and records coarse stage boundaries plus sampled Linux process-tree CPU/RSS/I/O
telemetry. It never imports campaign internals and cannot alter scientific authority.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import subprocess
import sys
import time
from typing import Any

_STAGE_RE = re.compile(
    r"(?:^\s*|^\[[^]]*?)(TARGET-DATA2[A-Z0-9-]*|DATA[0-9]+[A-Z0-9-]*|MVQUAL1|MVSEL2|REPAIR2|MVIDX1|STOR[1-5])\b"
)


def _format_hhmmss(seconds: float) -> str:
    total = max(0, int(round(float(seconds))))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _stage_from_line(line: str) -> str | None:
    match = _STAGE_RE.search(line[:160])
    return None if match is None else match.group(1)


def _proc_children(pid: int) -> tuple[int, ...]:
    try:
        text = Path(f"/proc/{pid}/task/{pid}/children").read_text(encoding="ascii")
    except OSError:
        return ()
    result: list[int] = []
    for value in text.split():
        try:
            result.append(int(value))
        except ValueError:
            continue
    return tuple(result)


def _process_tree(root_pid: int) -> tuple[int, ...]:
    pending = [int(root_pid)]
    seen: set[int] = set()
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        pending.extend(_proc_children(pid))
    return tuple(sorted(seen))


def _proc_stat(pid: int) -> tuple[float, float] | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        end = raw.rfind(")")
        if end < 0:
            return None
        fields = raw[end + 2 :].split()
        ticks = float(os.sysconf(os.sysconf_names["SC_CLK_TCK"]))
        return float(fields[11]) / ticks, float(fields[12]) / ticks
    except (OSError, ValueError, IndexError):
        return None


def _proc_status(pid: int) -> tuple[int, int]:
    rss_kib = 0
    threads = 0
    try:
        lines = Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines()
    except OSError:
        return rss_kib, threads
    for line in lines:
        if line.startswith("VmRSS:"):
            try:
                rss_kib = int(line.split()[1])
            except (ValueError, IndexError):
                pass
        elif line.startswith("Threads:"):
            try:
                threads = int(line.split()[1])
            except (ValueError, IndexError):
                pass
    return rss_kib, threads


def _proc_io(pid: int) -> tuple[int, int]:
    read_bytes = 0
    write_bytes = 0
    try:
        lines = Path(f"/proc/{pid}/io").read_text(encoding="ascii").splitlines()
    except OSError:
        return read_bytes, write_bytes
    for line in lines:
        if line.startswith("read_bytes:"):
            try:
                read_bytes = int(line.split()[1])
            except (ValueError, IndexError):
                pass
        elif line.startswith("write_bytes:"):
            try:
                write_bytes = int(line.split()[1])
            except (ValueError, IndexError):
                pass
    return read_bytes, write_bytes


class _ProcTreeTracker:
    def __init__(self, root_pid: int) -> None:
        self.root_pid = int(root_pid)
        self._last: dict[int, tuple[float, float, int, int]] = {}
        self.peak_rss_kib = 0
        self.peak_processes = 0
        self.peak_threads = 0

    def snapshot(self) -> dict[str, Any]:
        pids = _process_tree(self.root_pid)
        current_rss = 0
        current_threads = 0
        for pid in pids:
            cpu = _proc_stat(pid)
            if cpu is None:
                continue
            read_bytes, write_bytes = _proc_io(pid)
            self._last[pid] = (cpu[0], cpu[1], read_bytes, write_bytes)
            rss_kib, threads = _proc_status(pid)
            current_rss += rss_kib
            current_threads += threads
        self.peak_rss_kib = max(self.peak_rss_kib, current_rss)
        self.peak_processes = max(self.peak_processes, len(pids))
        self.peak_threads = max(self.peak_threads, current_threads)
        return {
            "user_cpu_seconds": sum(item[0] for item in self._last.values()),
            "system_cpu_seconds": sum(item[1] for item in self._last.values()),
            "read_bytes": sum(item[2] for item in self._last.values()),
            "write_bytes": sum(item[3] for item in self._last.values()),
            "current_rss_kib": current_rss,
            "current_processes": len(pids),
            "current_threads": current_threads,
            "seen_processes": len(self._last),
        }


def _delta(after: dict[str, Any], before: dict[str, Any], key: str) -> float | int:
    return after[key] - before[key]


def _stage_row(
    name: str,
    started: float,
    ended: float,
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    peak_rss_kib: int,
    peak_processes: int,
    peak_threads: int,
    transition_line: str | None,
) -> dict[str, Any]:
    wall = ended - started
    return {
        "stage": name,
        "wall_seconds": wall,
        "wall_hhmmss": _format_hhmmss(wall),
        "user_cpu_seconds_sampled": _delta(after, before, "user_cpu_seconds"),
        "system_cpu_seconds_sampled": _delta(after, before, "system_cpu_seconds"),
        "read_bytes_sampled": _delta(after, before, "read_bytes"),
        "write_bytes_sampled": _delta(after, before, "write_bytes"),
        "peak_rss_kib_sampled": peak_rss_kib,
        "peak_processes_sampled": peak_processes,
        "peak_threads_sampled": peak_threads,
        "transition_line": transition_line,
    }


def _terminate_group(process: subprocess.Popen[str], grace_seconds: float = 10.0) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return
    deadline = time.monotonic() + grace_seconds
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--sample-interval-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=0.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("supply the unchanged prepare command after --")
    if args.sample_interval_seconds <= 0.0:
        parser.error("--sample-interval-seconds must be positive")
    if args.timeout_seconds < 0.0:
        parser.error("--timeout-seconds cannot be negative")

    output = args.output.resolve()
    log_path = (args.log or output.with_suffix(".log")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    timed_out = False
    interrupted = False
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdout is not None
    tracker = _ProcTreeTracker(process.pid)
    baseline = tracker.snapshot()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    current_stage = "startup"
    stage_started = started
    stage_before = baseline
    stage_peak_rss = int(baseline["current_rss_kib"])
    stage_peak_processes = int(baseline["current_processes"])
    stage_peak_threads = int(baseline["current_threads"])
    stage_rows: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    next_sample = started + args.sample_interval_seconds
    deadline = None if args.timeout_seconds == 0.0 else started + args.timeout_seconds

    with log_path.open("w", encoding="utf-8", buffering=1) as log:
        try:
            while True:
                now = time.monotonic()
                if deadline is not None and now >= deadline and process.poll() is None:
                    timed_out = True
                    _terminate_group(process)

                timeout = max(0.0, min(next_sample - now, 0.5))
                events = selector.select(timeout)
                for key, _ in events:
                    line = key.fileobj.readline()
                    if not line:
                        continue
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    log.write(line)
                    stage = _stage_from_line(line)
                    if stage is not None and stage != current_stage:
                        snap = tracker.snapshot()
                        transition_time = time.monotonic()
                        stage_rows.append(
                            _stage_row(
                                current_stage,
                                stage_started,
                                transition_time,
                                stage_before,
                                snap,
                                peak_rss_kib=stage_peak_rss,
                                peak_processes=stage_peak_processes,
                                peak_threads=stage_peak_threads,
                                transition_line=line.rstrip()[:500],
                            )
                        )
                        transitions.append({
                            "at_seconds": transition_time - started,
                            "from": current_stage,
                            "to": stage,
                            "line": line.rstrip()[:500],
                        })
                        current_stage = stage
                        stage_started = transition_time
                        stage_before = snap
                        stage_peak_rss = int(snap["current_rss_kib"])
                        stage_peak_processes = int(snap["current_processes"])
                        stage_peak_threads = int(snap["current_threads"])

                now = time.monotonic()
                if now >= next_sample:
                    snap = tracker.snapshot()
                    stage_peak_rss = max(stage_peak_rss, int(snap["current_rss_kib"]))
                    stage_peak_processes = max(stage_peak_processes, int(snap["current_processes"]))
                    stage_peak_threads = max(stage_peak_threads, int(snap["current_threads"]))
                    next_sample = now + args.sample_interval_seconds

                if process.poll() is not None:
                    for line in process.stdout:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        log.write(line)
                    break
        except KeyboardInterrupt:
            interrupted = True
            _terminate_group(process)
        finally:
            selector.close()

    returncode = process.wait()
    final_snapshot = tracker.snapshot()
    ended = time.monotonic()
    stage_peak_rss = max(stage_peak_rss, int(final_snapshot["current_rss_kib"]))
    stage_peak_processes = max(stage_peak_processes, int(final_snapshot["current_processes"]))
    stage_peak_threads = max(stage_peak_threads, int(final_snapshot["current_threads"]))
    stage_rows.append(
        _stage_row(
            current_stage,
            stage_started,
            ended,
            stage_before,
            final_snapshot,
            peak_rss_kib=stage_peak_rss,
            peak_processes=stage_peak_processes,
            peak_threads=stage_peak_threads,
            transition_line=None,
        )
    )

    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall = ended - started
    payload = {
        "schema": "mdstats.benchmark.prepare-o0.v1",
        "source": {"git_head": _git_head()},
        "command": command,
        "execution": {
            "returncode": returncode,
            "timed_out": timed_out,
            "interrupted": interrupted,
            "wall_seconds": wall,
            "wall_hhmmss": _format_hhmmss(wall),
            "sample_interval_seconds": args.sample_interval_seconds,
            "timeout_seconds": args.timeout_seconds,
            "log_path": str(log_path),
            "child_user_cpu_seconds": usage_after.ru_utime - usage_before.ru_utime,
            "child_system_cpu_seconds": usage_after.ru_stime - usage_before.ru_stime,
            "child_maxrss_kib": int(usage_after.ru_maxrss),
            "child_major_faults": int(usage_after.ru_majflt - usage_before.ru_majflt),
            "child_minor_faults": int(usage_after.ru_minflt - usage_before.ru_minflt),
            "child_filesystem_inputs": int(usage_after.ru_inblock - usage_before.ru_inblock),
            "child_filesystem_outputs": int(usage_after.ru_oublock - usage_before.ru_oublock),
            "sampled_peak_rss_kib": tracker.peak_rss_kib,
            "sampled_peak_processes": tracker.peak_processes,
            "sampled_peak_threads": tracker.peak_threads,
            "sampled_seen_processes": int(final_snapshot["seen_processes"]),
        },
        "stage_segments": stage_rows,
        "stage_transitions": transitions,
        "measurement_notes": [
            "The wrapped campaign command is unchanged; this file is benchmark evidence only.",
            "Stage CPU/I/O counters are sampled from /proc for the observed process tree and are diagnostic, not scientific authority.",
            "Very short-lived descendants between samples can be missed; whole-command RUSAGE_CHILDREN counters are retained separately.",
            "Stage labels are inferred only from leading/bracketed canonical progress tokens; unrecognized intervals remain attached to the last observed stage.",
        ],
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "returncode": returncode,
                "timed_out": timed_out,
                "wall_hhmmss": _format_hhmmss(wall),
                "output": str(output),
                "log": str(log_path),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    if interrupted:
        return 130
    if timed_out and returncode == 0:
        return 124
    return int(returncode)


if __name__ == "__main__":
    raise SystemExit(main())
