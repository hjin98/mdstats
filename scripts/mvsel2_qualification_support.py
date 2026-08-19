"""Protocol-3.1 resource supervision for REV8 MVSEL2 qualification."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from typing import Any, Mapping, Sequence

GIB = 1024 ** 3
MIB = 1024 ** 2
OWNER_SCHEMA = "mdstats.mvsel2-qualification-owner.v2"
STATE_SCHEMA = "mdstats.mvsel2-lightweight-qualification.state.v2"
SUMMARY_SCHEMA = "mdstats.mvsel2-lightweight-qualification.summary.v2"
DEFAULT_TOTAL_SECONDS = 15 * 60
DEFAULT_SCRATCH_BYTES = GIB
WATCH_INTERVAL_SECONDS = 1.0
LIMIT_GRACE_SAMPLES = 2
QUIESCENCE_SECONDS = 0.5


@dataclass(frozen=True)
class ResourcePlan:
    cpu_count: int
    host_available_bytes: int | None
    cgroup_available_bytes: int | None
    effective_available_bytes: int
    hard_rss_bytes: int
    operating_rss_bytes: int
    hard_scratch_bytes: int
    operating_scratch_bytes: int
    hard_total_seconds: float
    operating_total_seconds: float
    free_disk_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_count": self.cpu_count,
            "host_available_bytes": self.host_available_bytes,
            "cgroup_available_bytes": self.cgroup_available_bytes,
            "effective_available_bytes": self.effective_available_bytes,
            "hard_rss_bytes": self.hard_rss_bytes,
            "operating_rss_bytes": self.operating_rss_bytes,
            "hard_scratch_bytes": self.hard_scratch_bytes,
            "operating_scratch_bytes": self.operating_scratch_bytes,
            "hard_total_seconds": self.hard_total_seconds,
            "operating_total_seconds": self.operating_total_seconds,
            "free_disk_bytes": self.free_disk_bytes,
        }


def json_dump(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def json_load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * MIB), b""):
            result.update(chunk)
    return result.hexdigest()


def _file_identity(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    stat = path.stat()
    return {
        "path": str(path),
        "sha256": sha256(path),
        "size_bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def production_identity(database: Path, config: Path | None) -> dict[str, Any]:
    """Capture the material SQLite/config authority, including WAL content.

    SQLite ``-shm`` is deliberately excluded: read transactions can change
    reader marks in shared memory without changing database content.  A WAL or
    rollback journal, when present, is part of the material database state and
    is therefore hashed and compared.
    """

    database_identity = _file_identity(database)
    if database_identity is None:
        raise RuntimeError(f"production database is missing: {database}")
    result: dict[str, Any] = {
        "database": database_identity,
        "database_wal": _file_identity(Path(str(database) + "-wal")),
        "database_journal": _file_identity(Path(str(database) + "-journal")),
    }
    if config is not None:
        config_identity = _file_identity(config)
        if config_identity is None:
            raise RuntimeError(f"campaign config is missing: {config}")
        result["config"] = config_identity
    return result


def read_memavailable() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _read_int_file(path: Path) -> int | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not value or value == "max":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def cgroup_available() -> int | None:
    root = Path("/sys/fs/cgroup")
    maximum = _read_int_file(root / "memory.max")
    current = _read_int_file(root / "memory.current")
    if maximum is None or current is None or maximum <= current:
        return None
    return maximum - current


def _cpu_count() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, int(os.cpu_count() or 1))


def derive_resource_plan(
    *,
    root: Path,
    max_rss_gib: float | None = None,
    max_scratch_gib: float | None = None,
    total_seconds: float | None = None,
) -> ResourcePlan:
    """Derive hard containment and a smaller normal operating envelope.

    User-supplied values may only tighten the automatic Protocol-3.1 defaults;
    they never raise the discovered/default safety boundary.
    """

    host = read_memavailable()
    cgroup = cgroup_available()
    available = [value for value in (host, cgroup) if value is not None and value > 0]
    effective = min(available) if available else 8 * GIB

    reserve = max(2 * GIB, int(0.20 * effective))
    hard_rss = max(1 * GIB, min(int(0.75 * effective), effective - reserve))
    if max_rss_gib is not None:
        if max_rss_gib <= 0:
            raise RuntimeError("--max-rss-gib must be positive")
        hard_rss = min(hard_rss, int(max_rss_gib * GIB))
    if hard_rss < 1536 * MIB:
        raise RuntimeError(
            "safe RSS containment is below the minimum qualification envelope"
        )
    operating_rss = min(int(0.70 * hard_rss), hard_rss - 512 * MIB)

    free_disk = shutil.disk_usage(root).free
    hard_scratch = min(DEFAULT_SCRATCH_BYTES, max(128 * MIB, free_disk // 8))
    if max_scratch_gib is not None:
        if max_scratch_gib <= 0:
            raise RuntimeError("--max-scratch-gib must be positive")
        hard_scratch = min(hard_scratch, int(max_scratch_gib * GIB))
    operating_scratch = max(
        64 * MIB,
        min(512 * MIB, int(0.60 * hard_scratch)),
    )

    if total_seconds is not None and float(total_seconds) <= 0:
        raise RuntimeError("--total-timeout-seconds must be positive")
    hard_seconds = (
        DEFAULT_TOTAL_SECONDS
        if total_seconds is None
        else min(DEFAULT_TOTAL_SECONDS, float(total_seconds))
    )
    operating_seconds = max(60.0, 0.65 * hard_seconds)

    return ResourcePlan(
        cpu_count=_cpu_count(),
        host_available_bytes=host,
        cgroup_available_bytes=cgroup,
        effective_available_bytes=effective,
        hard_rss_bytes=hard_rss,
        operating_rss_bytes=operating_rss,
        hard_scratch_bytes=hard_scratch,
        operating_scratch_bytes=operating_scratch,
        hard_total_seconds=hard_seconds,
        operating_total_seconds=operating_seconds,
        free_disk_bytes=free_disk,
    )


def physical_tree_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    seen: set[tuple[int, int]] = set()
    for base, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
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


def _pgrp(pid: int) -> int | None:
    try:
        text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = text.rsplit(")", 1)[1].strip().split()
        return int(fields[2])  # state, ppid, pgrp
    except (OSError, ValueError, IndexError):
        return None


def rss_bytes(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def process_group_rss_bytes(pgid: int) -> int:
    total = 0
    try:
        children = tuple(Path("/proc").iterdir())
    except OSError:
        return 0
    for child in children:
        if not child.name.isdigit():
            continue
        pid = int(child.name)
        if _pgrp(pid) != pgid:
            continue
        value = rss_bytes(pid)
        if value is not None:
            total += value
    return total


def _pid_start_ticks(pid: int) -> int | None:
    try:
        text = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = text.rsplit(")", 1)[1].strip().split()
        return int(fields[19])  # field 22 overall: starttime
    except (OSError, ValueError, IndexError):
        return None


def _same_live_process(pid: int, start_ticks: int | None) -> bool:
    if pid <= 0:
        return False
    current = _pid_start_ticks(pid)
    return current is not None and (start_ticks is None or current == start_ticks)


def _owner(path: Path, expected_parent: Path) -> dict[str, Any] | None:
    try:
        payload = json_load(path / "OWNER.json")
        recorded = Path(str(payload["scratch_dir"])).resolve()
    except Exception:
        return None
    if payload.get("schema") != OWNER_SCHEMA:
        return None
    if recorded != path.resolve() or path.parent.resolve() != expected_parent.resolve():
        return None
    return payload


def scavenge_owned_scratch(scratch_parent: Path) -> list[str]:
    """Remove only abandoned scratch whose ownership manifest is valid."""

    removed: list[str] = []
    scratch_parent.mkdir(parents=True, exist_ok=True)
    for path in scratch_parent.iterdir():
        if not path.is_dir():
            continue
        owner = _owner(path, scratch_parent)
        if owner is None:
            continue
        pid = int(owner.get("parent_pid", -1))
        ticks = owner.get("parent_start_ticks")
        ticks = None if ticks is None else int(ticks)
        if _same_live_process(pid, ticks):
            continue
        shutil.rmtree(path, ignore_errors=True)
        removed.append(path.name)
    return removed


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        process.terminate()
    deadline = time.monotonic() + 8.0
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()


def repair_projection_upper(
    rows: Sequence[Mapping[str, Any]],
    *,
    candidate_count: int,
    materializable_sizes: Sequence[int],
    removal_shortlist_limit: int,
    max_swaps_per_shell: int,
    max_passes_per_shell: int,
) -> float | None:
    usable = [row for row in rows if int(row.get("proposals", 0)) > 0]
    if not usable:
        return None
    unit_seconds = max(
        float(row["wall_seconds"])
        / max(1, int(row["shell_size"]) + int(row["proposals"]) * candidate_count)
        for row in usable
    )
    proposal_cap = removal_shortlist_limit * (
        max_swaps_per_shell + max_passes_per_shell
    )
    previous = 0
    total_work = 0
    for size in materializable_sizes:
        size = int(size)
        shell = max(0, size - previous)
        total_work += shell + proposal_cap * candidate_count
        previous = size
    return 4.0 * unit_seconds * total_work


def selector_projection_upper(
    *,
    current_restore_seconds: float,
    historical_cold_preflight_seconds: float,
    phase_a_prefix_size: int,
    max_phase_a_rank_seconds: float,
    measured_phase_a_seconds: float,
    exact_rebase_seconds: float,
    phase_a_end: int,
    max_phase_b_rank_seconds: float,
    target_size: int,
) -> float:
    setup = max(
        2.0 * current_restore_seconds,
        4.0 * historical_cold_preflight_seconds,
    )
    prefix = phase_a_prefix_size * max_phase_a_rank_seconds
    remaining = max(0, target_size - phase_a_end)
    return 1.25 * (
        setup
        + prefix
        + measured_phase_a_seconds
        + exact_rebase_seconds
        + remaining * max_phase_b_rank_seconds
    )


def _trim_evidence(evidence_parent: Path, keep: int = 5) -> None:
    runs = sorted(
        (path for path in evidence_parent.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old in runs[keep:]:
        shutil.rmtree(old, ignore_errors=True)


def _publish_preflight_block(
    *,
    root: Path,
    evidence: Path,
    state_path: Path,
    run_id: str,
    plan: ResourcePlan,
    scavenged: list[str],
    first_identity: Mapping[str, Any],
    second_identity: Mapping[str, Any],
) -> int:
    summary = {
        "schema": SUMMARY_SCHEMA,
        "run_id": run_id,
        "status": "BLOCKED",
        "classification": "EXTERNAL_INPUT_NOT_QUIESCENT",
        "returncode": None,
        "limit_reason": None,
        "elapsed_seconds": 0.0,
        "peak_owned_process_rss_bytes": 0,
        "peak_scratch_physical_bytes": 0,
        "resource_plan": plan.to_dict(),
        "production_identity_before": first_identity,
        "production_identity_after": second_identity,
        "worker_evidence": None,
        "startup_scavenged": scavenged,
        "codex_required": False,
        "full_mdstats_snapshot_created": False,
    }
    json_dump(evidence / "summary.json", summary)
    json_dump(root / "summary.json", summary)
    json_dump(
        state_path,
        {
            "schema": STATE_SCHEMA,
            "run_id": run_id,
            "status": "BLOCKED",
            "classification": "EXTERNAL_INPUT_NOT_QUIESCENT",
            "resource_plan": plan.to_dict(),
            "startup_scavenged": scavenged,
            "summary": str(evidence / "summary.json"),
        },
    )
    return 3


def run_supervised_worker(
    *,
    command: list[str],
    repo: Path,
    database: Path,
    config: Path | None,
    root: Path,
    plan: ResourcePlan,
) -> int:
    """Run one qualification worker under hard external containment."""

    evidence_parent = root / "evidence"
    scratch_parent = root / "scratch"
    evidence_parent.mkdir(parents=True, exist_ok=True)
    scratch_parent.mkdir(parents=True, exist_ok=True)
    scavenged = scavenge_owned_scratch(scratch_parent)

    run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}"
    evidence = evidence_parent / run_id
    scratch = scratch_parent / run_id
    evidence.mkdir(parents=True)
    scratch.mkdir(parents=True)
    state_path = root / "state.json"

    first_identity = production_identity(database, config)
    time.sleep(QUIESCENCE_SECONDS)
    before = production_identity(database, config)
    if first_identity != before:
        shutil.rmtree(scratch, ignore_errors=True)
        result = _publish_preflight_block(
            root=root,
            evidence=evidence,
            state_path=state_path,
            run_id=run_id,
            plan=plan,
            scavenged=scavenged,
            first_identity=first_identity,
            second_identity=before,
        )
        _trim_evidence(evidence_parent)
        return result

    json_dump(
        scratch / "OWNER.json",
        {
            "schema": OWNER_SCHEMA,
            "run_id": run_id,
            "qualifier": str(Path(command[1]).resolve()),
            "scratch_dir": str(scratch),
            "parent_pid": os.getpid(),
            "parent_start_ticks": _pid_start_ticks(os.getpid()),
            "production_identity": before,
        },
    )
    state: dict[str, Any] = {
        "schema": STATE_SCHEMA,
        "run_id": run_id,
        "status": "RUNNING",
        "production_identity": before,
        "resource_plan": plan.to_dict(),
        "startup_scavenged": scavenged,
    }
    json_dump(state_path, state)

    worker_command = command + [
        "--worker-scratch",
        str(scratch),
        "--worker-evidence",
        str(evidence),
        "--operating-rss-bytes",
        str(plan.operating_rss_bytes),
        "--operating-seconds",
        str(plan.operating_total_seconds),
    ]
    log_path = evidence / "worker.log"
    process: subprocess.Popen[str] | None = None
    peak_rss = 0
    peak_scratch = 0
    limit_reason: str | None = None
    interrupted = False
    rss_over = 0
    scratch_over = 0
    started = time.monotonic()

    def handle_signal(_signum: int, _frame: Any) -> None:
        nonlocal interrupted
        interrupted = True
        if process is not None:
            terminate(process)

    previous_handlers = {
        item: signal.signal(item, handle_signal)
        for item in (signal.SIGINT, signal.SIGTERM)
    }

    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                worker_command,
                cwd=repo,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
                env={
                    **os.environ,
                    "OMP_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                    "NUMEXPR_NUM_THREADS": "1",
                },
            )
            while process.poll() is None:
                rss = process_group_rss_bytes(process.pid)
                scratch_bytes = physical_tree_bytes(scratch)
                peak_rss = max(peak_rss, rss)
                peak_scratch = max(peak_scratch, scratch_bytes)
                rss_over = rss_over + 1 if rss > plan.hard_rss_bytes else 0
                scratch_over = (
                    scratch_over + 1
                    if scratch_bytes > plan.hard_scratch_bytes
                    else 0
                )
                elapsed = time.monotonic() - started
                host_now = read_memavailable()
                cgroup_now = cgroup_available()
                pressure_floor = max(GIB, int(0.08 * plan.effective_available_bytes))

                if rss_over >= LIMIT_GRACE_SAMPLES:
                    limit_reason = (
                        f"RSS_LIMIT_EXCEEDED:{rss}>{plan.hard_rss_bytes}"
                    )
                elif scratch_over >= LIMIT_GRACE_SAMPLES:
                    limit_reason = (
                        "SCRATCH_LIMIT_EXCEEDED:"
                        f"{scratch_bytes}>{plan.hard_scratch_bytes}"
                    )
                elif elapsed > plan.hard_total_seconds:
                    limit_reason = (
                        f"TIME_LIMIT_EXCEEDED:{elapsed:.1f}>"
                        f"{plan.hard_total_seconds:.1f}"
                    )
                elif host_now is not None and host_now < pressure_floor:
                    limit_reason = "HOST_MEMORY_PRESSURE"
                elif cgroup_now is not None and cgroup_now < pressure_floor:
                    limit_reason = "CGROUP_MEMORY_PRESSURE"

                if limit_reason is not None:
                    terminate(process)
                    break
                time.sleep(WATCH_INTERVAL_SECONDS)
            returncode = process.wait()

        after = production_identity(database, config)
        worker_file = evidence / "worker.json"
        worker = json_load(worker_file) if worker_file.is_file() else None
        if after != before:
            status = "BLOCKED"
            classification = "EXTERNAL_INPUT_CHANGED"
        elif interrupted:
            status = "BLOCKED"
            classification = "INTERRUPTED"
        elif limit_reason is not None:
            status = "BLOCKED"
            classification = "QUALIFICATION_RESOURCE_MODEL_FAILURE"
        elif worker is None:
            status = "BLOCKED"
            classification = "WORKER_NO_EVIDENCE"
        elif worker.get("failure_class") == "PRODUCT_OR_MATERIAL_CHECK_ERROR":
            # The worker's catch-all cannot distinguish product defects from
            # malformed/missing external input or a harness defect.  Protocol
            # 3.1 therefore fails closed as BLOCKED instead of falsely
            # disqualifying the product.  Explicit measured stage FAIL results
            # (for example the frozen <10x performance floor) remain FAIL.
            status = "BLOCKED"
            classification = "HARNESS_OR_INPUT_BLOCKED"
        else:
            status = str(worker.get("status", "BLOCKED"))
            classification = "MATERIAL_RESULT"

        summary = {
            "schema": SUMMARY_SCHEMA,
            "run_id": run_id,
            "status": status,
            "classification": classification,
            "returncode": returncode,
            "limit_reason": limit_reason,
            "elapsed_seconds": time.monotonic() - started,
            "peak_owned_process_rss_bytes": peak_rss,
            "peak_scratch_physical_bytes": peak_scratch,
            "resource_plan": plan.to_dict(),
            "production_identity_before": before,
            "production_identity_after": after,
            "worker_evidence": worker,
            "startup_scavenged": scavenged,
            "codex_required": False,
            "full_mdstats_snapshot_created": False,
        }
        json_dump(evidence / "summary.json", summary)
        json_dump(root / "summary.json", summary)
        state.update(
            status=status,
            classification=classification,
            summary=str(evidence / "summary.json"),
        )
        json_dump(state_path, state)
        return 0 if status == "PASS" else (2 if status == "FAIL" else 3)
    finally:
        for item, handler in previous_handlers.items():
            signal.signal(item, handler)
        if process is not None and process.poll() is None:
            terminate(process)
        shutil.rmtree(scratch, ignore_errors=True)
        if log_path.is_file() and log_path.stat().st_size > 256 * 1024:
            log_path.write_bytes(log_path.read_bytes()[-256 * 1024 :])
        _trim_evidence(evidence_parent)
