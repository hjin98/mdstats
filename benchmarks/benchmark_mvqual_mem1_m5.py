#!/usr/bin/env python3
"""M5 product meter for bounded exact TARGET-DATA2C-MVQUAL2.

This benchmark reopens the persisted v5 campaign authorities and invokes the
direct fixed-eight ``build_target_multi_view_qualification_plan_v2`` owner. It
deliberately does not run ``prepare`` or persist a rebuilt MVQUAL2 authority.
Each repetition executes in a bounded child process so a pathological product
run can be terminated without leaving Python worker threads alive.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time
from typing import Any, Mapping

import mdstats
from mdstats.training_data import campaign_cli as campaign
from mdstats.training_data.progress_timing import format_progress_time
from mdstats.training_data.resources import build_stage_resource_scope

_SCHEMA = "mdstats.benchmark.mvqual-mem1-m5.v1"
_RUN_SCHEMA = "mdstats.benchmark.mvqual-mem1-m5-run.v1"
_DEFAULT_STRICT_EDGES = 1_048_576
_DEFAULT_PRODUCT_CANDIDATES = 36_408
_DEFAULT_PRODUCT_FAMILIES = 165
_DEFAULT_PRODUCT_FORWARD_EDGES = 9_505_021_522
_DEFAULT_PRODUCT_MAX_SIZE = 16_384


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _git_head() -> str:
    root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _usage() -> dict[str, float | int]:
    value = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "user_cpu_seconds": float(value.ru_utime),
        "system_cpu_seconds": float(value.ru_stime),
        "minor_faults": int(value.ru_minflt),
        "major_faults": int(value.ru_majflt),
        "filesystem_inputs": int(value.ru_inblock),
        "filesystem_outputs": int(value.ru_oublock),
        "lifetime_peak_rss_kib": int(value.ru_maxrss),
    }


def _usage_delta(
    before: Mapping[str, float | int], after: Mapping[str, float | int]
) -> dict[str, float | int]:
    result: dict[str, float | int] = {}
    for key in (
        "user_cpu_seconds",
        "system_cpu_seconds",
        "minor_faults",
        "major_faults",
        "filesystem_inputs",
        "filesystem_outputs",
    ):
        result[key] = after[key] - before[key]  # type: ignore[operator]
    result["lifetime_peak_rss_kib"] = int(after["lifetime_peak_rss_kib"])
    return result


def _read_colon_ints(path: Path) -> dict[str, int] | None:
    try:
        result: dict[str, int] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            token = raw.strip().split()[0]
            result[key.strip()] = int(token)
        return result
    except (OSError, ValueError, IndexError):
        return None


def _proc_status_kib() -> dict[str, int | None]:
    values = _read_colon_ints(Path("/proc/self/status")) or {}
    return {
        "rss_kib": values.get("VmRSS"),
        "swap_kib": values.get("VmSwap"),
    }


def _proc_io() -> dict[str, int] | None:
    values = _read_colon_ints(Path("/proc/self/io"))
    if values is None:
        return None
    return {
        "read_bytes": int(values.get("read_bytes", 0)),
        "write_bytes": int(values.get("write_bytes", 0)),
    }


def _dict_delta(
    before: Mapping[str, int] | None, after: Mapping[str, int] | None
) -> dict[str, int] | None:
    if before is None or after is None:
        return None
    keys = sorted(set(before) | set(after))
    return {key: int(after.get(key, 0)) - int(before.get(key, 0)) for key in keys}


def _vmstat_swap() -> dict[str, int] | None:
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/vmstat").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] in {"pswpin", "pswpout"}:
                values[parts[0]] = int(parts[1])
        return {"pswpin": values.get("pswpin", 0), "pswpout": values.get("pswpout", 0)}
    except (OSError, ValueError):
        return None


def _meminfo_kib() -> dict[str, int | None]:
    values = _read_colon_ints(Path("/proc/meminfo")) or {}
    return {
        "mem_total_kib": values.get("MemTotal"),
        "mem_available_kib": values.get("MemAvailable"),
    }


class _MemorySampler:
    """Low-overhead Linux process/system-memory sampler for the builder window."""

    def __init__(self, interval_seconds: float = 0.20) -> None:
        self.interval_seconds = max(0.05, float(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.sample_count = 0
        self.rss_kib_before: int | None = None
        self.rss_kib_peak: int | None = None
        self.rss_kib_after: int | None = None
        self.swap_kib_before: int | None = None
        self.swap_kib_peak: int | None = None
        self.swap_kib_after: int | None = None
        self.mem_total_kib: int | None = None
        self.mem_available_kib_before: int | None = None
        self.mem_available_kib_min: int | None = None
        self.mem_available_kib_after: int | None = None

    def _sample(self) -> None:
        status = _proc_status_kib()
        memory = _meminfo_kib()
        rss = status["rss_kib"]
        swap = status["swap_kib"]
        available = memory["mem_available_kib"]
        if self.sample_count == 0:
            self.rss_kib_before = rss
            self.swap_kib_before = swap
            self.mem_total_kib = memory["mem_total_kib"]
            self.mem_available_kib_before = available
        if rss is not None:
            self.rss_kib_peak = rss if self.rss_kib_peak is None else max(self.rss_kib_peak, rss)
        if swap is not None:
            self.swap_kib_peak = swap if self.swap_kib_peak is None else max(self.swap_kib_peak, swap)
        if available is not None:
            self.mem_available_kib_min = (
                available
                if self.mem_available_kib_min is None
                else min(self.mem_available_kib_min, available)
            )
        self.sample_count += 1

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._sample()

    def start(self) -> None:
        self._sample()
        self._thread = threading.Thread(
            target=self._run,
            name="mdstats-mvqual-m5-rss",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, 5.0 * self.interval_seconds))
        self._sample()
        final_status = _proc_status_kib()
        final_memory = _meminfo_kib()
        self.rss_kib_after = final_status["rss_kib"]
        self.swap_kib_after = final_status["swap_kib"]
        self.mem_available_kib_after = final_memory["mem_available_kib"]
        if self.rss_kib_after is not None:
            self.rss_kib_peak = (
                self.rss_kib_after
                if self.rss_kib_peak is None
                else max(self.rss_kib_peak, self.rss_kib_after)
            )
        if self.swap_kib_after is not None:
            self.swap_kib_peak = (
                self.swap_kib_after
                if self.swap_kib_peak is None
                else max(self.swap_kib_peak, self.swap_kib_after)
            )
        if self.mem_available_kib_after is not None:
            self.mem_available_kib_min = (
                self.mem_available_kib_after
                if self.mem_available_kib_min is None
                else min(self.mem_available_kib_min, self.mem_available_kib_after)
            )
        return {
            "sample_count": self.sample_count,
            "rss_kib_before": self.rss_kib_before,
            "rss_kib_peak": self.rss_kib_peak,
            "rss_kib_after": self.rss_kib_after,
            "rss_increment_kib": (
                None
                if self.rss_kib_before is None or self.rss_kib_peak is None
                else max(0, self.rss_kib_peak - self.rss_kib_before)
            ),
            "swap_kib_before": self.swap_kib_before,
            "swap_kib_peak": self.swap_kib_peak,
            "swap_kib_after": self.swap_kib_after,
            "swap_growth_kib": (
                None
                if self.swap_kib_before is None or self.swap_kib_peak is None
                else max(0, self.swap_kib_peak - self.swap_kib_before)
            ),
            "mem_total_kib": self.mem_total_kib,
            "mem_available_kib_before": self.mem_available_kib_before,
            "mem_available_kib_min": self.mem_available_kib_min,
            "mem_available_kib_after": self.mem_available_kib_after,
        }


class _QueueSummary:
    """Bounded aggregation of PARCORE1 snapshots."""

    _MAX_FIELDS = (
        "allocated_workers",
        "busy_workers",
        "max_busy_workers",
        "ready_tasks",
        "inflight_tasks",
        "completed_tasks",
        "ready_memory_bytes",
        "inflight_memory_bytes",
        "completed_memory_bytes",
        "reserved_memory_bytes",
        "peak_accounted_memory_bytes",
        "memory_backpressure_events",
        "queue_backpressure_events",
        "heartbeat_count",
    )

    def __init__(self) -> None:
        self.snapshot_count = 0
        self.final: dict[str, Any] | None = None
        self.maximum: dict[str, int] = {key: 0 for key in self._MAX_FIELDS}

    def __call__(self, snapshot: Any) -> None:
        payload = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot)
        self.snapshot_count += 1
        self.final = dict(payload)
        for key in self._MAX_FIELDS:
            value = payload.get(key)
            if value is not None:
                self.maximum[key] = max(self.maximum[key], int(value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_count": self.snapshot_count,
            "maximum": self.maximum,
            "final": self.final,
        }


def _sparse_counts(index: Any) -> dict[str, Any]:
    domains: list[dict[str, Any]] = []
    for domain in index.domains:
        forward_edges = int(sum(int(family.edge_count) for family in domain.families))
        domains.append(
            {
                "label_domain_id": str(domain.label_domain_id),
                "candidate_count": int(domain.candidate_count),
                "family_count": len(domain.families),
                "forward_edge_count": forward_edges,
            }
        )
    return {
        "domain_count": len(domains),
        "candidate_count_total": sum(item["candidate_count"] for item in domains),
        "family_count_total": sum(item["family_count"] for item in domains),
        "forward_edge_count_total": sum(item["forward_edge_count"] for item in domains),
        "domains": domains,
    }


def _completed_sizes(job_telemetry: list[dict[str, Any]]) -> dict[str, list[int]]:
    values: dict[str, set[int]] = {}
    for item in job_telemetry:
        values.setdefault(str(item["selector"]), set()).add(int(item["target_size"]))
    return {key: sorted(sizes) for key, sizes in sorted(values.items())}


def _single_run(args: argparse.Namespace) -> int:
    """Measure one exact MVQUAL2 rebuild from persisted v5 authorities."""

    from mdstats.training_data import target_multi_view_qualification_v2 as mvqual_v2

    total_usage_before = _usage()
    total_io_before = _proc_io()
    total_started = time.perf_counter()

    cfg, paths = campaign._load_config(args.campaign_config)
    database = paths.state_db.resolve()
    if not database.is_file():
        raise RuntimeError(f"campaign database does not exist: {database}")

    requested_workers = int(
        cfg.get("performance", {}).get("target_multi_view_qualification_workers", 0)
    )
    effective_workers, detected_resources = campaign._target_multi_view_qualification_parallelism(cfg)
    scope = build_stage_resource_scope(
        detected_resources,
        stage_name="TARGET-DATA2C-MVQUAL2",
        python_workers=effective_workers,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
    )

    load_usage_before = _usage()
    load_io_before = _proc_io()
    load_started = time.perf_counter()
    store = campaign.CampaignStore(database)
    try:
        reference = store.get_record("target_coverage_reference", mdstats.TargetCoverageReference)
        sparse_index = store.get_record(
            "target_coverage_sparse_index", mdstats.TargetCoverageSparseIndex
        )
        feasibility = store.get_record(
            "target_coverage_feasibility", mdstats.TargetCoverageFeasibilityReport
        )
        role_freeze = store.get_record("target_data_role_freeze", mdstats.TargetDataRoleFreeze)
        repair_plan = store.get_record(
            "target_multi_view_repair_v2", mdstats.TargetMultiViewRepairPlanV2
        )
        try:
            persisted_qualification = store.get_record_optional(
                "target_multi_view_qualification_v2", mdstats.TargetMultiViewQualificationPlanV2
            )
        except Exception:
            persisted_qualification = None

        load_wall = time.perf_counter() - load_started
        load_usage_after = _usage()
        load_io_after = _proc_io()

        authority_digests = {
            "target_coverage_reference": reference.content_digest,
            "target_coverage_sparse_index": sparse_index.content_digest,
            "target_coverage_feasibility": feasibility.content_digest,
            "target_data_role_freeze": role_freeze.content_digest,
            "target_multi_view_repair_v2": repair_plan.content_digest,
            "persisted_target_multi_view_qualification_v2": (
                None if persisted_qualification is None else persisted_qualification.content_digest
            ),
        }
        sparse_counts = _sparse_counts(sparse_index)
        policy = mdstats.TargetMultiViewQualificationPolicyV2(
            coverage_threshold=float(reference.policy.coverage_threshold)
        )

        job_telemetry: list[dict[str, Any]] = []
        original_score_job = mvqual_v2._mvqual_score_job

        def capture_score_job(*score_args: Any, **score_kwargs: Any) -> Any:
            result = original_score_job(*score_args, **score_kwargs)
            job_telemetry.append(
                {
                    "selector": str(result.selector),
                    "label_domain_id": str(result.label_domain_id),
                    "target_size": int(result.target_size),
                    "streamed_edge_count": int(result.streamed_edge_count),
                    "maximum_chunk_edges": int(result.maximum_chunk_edges),
                    "maximum_selected_row_edges": int(result.maximum_selected_row_edges),
                    "estimated_peak_bytes": 0,
                    "direct_seconds": float(result.direct_seconds),
                    "sparse_seconds": float(result.sparse_seconds),
                    "crosscheck_seconds": float(result.crosscheck_seconds),
                    "hard_seconds": float(result.hard_seconds),
                }
            )
            return result

        sampler = _MemorySampler()
        sampler.start()
        builder_usage_before = _usage()
        builder_io_before = _proc_io()
        swap_before = _vmstat_swap()
        builder_started = time.perf_counter()
        mvqual_v2._mvqual_score_job = capture_score_job
        try:
            plan = mdstats.build_target_multi_view_qualification_plan_v2(
                reference,
                sparse_index,
                feasibility,
                role_freeze,
                repair_plan,
                policy=policy,
                coverage_query_workers=1,
                scoring_workers=effective_workers,
                sparse_max_edges=int(args.sparse_max_edges),
                progress_callback=lambda message: print(
                    f"[MVQUAL-MEM1-M5] {message}", flush=True
                ),
            )
        finally:
            mvqual_v2._mvqual_score_job = original_score_job
        mdstats.validate_target_multi_view_qualification_authority_v2(
            plan,
            target_coverage_reference=reference,
            target_coverage_sparse_index=sparse_index,
            target_coverage_feasibility=feasibility,
            target_data_role_freeze=role_freeze,
            target_multi_view_repair=repair_plan,
            policy=policy,
        )
        builder_wall = time.perf_counter() - builder_started
        swap_after = _vmstat_swap()
        builder_io_after = _proc_io()
        builder_usage_after = _usage()
        memory = sampler.stop()

        completed_sizes = _completed_sizes(job_telemetry)
        max_chunk = max(
            (int(item["maximum_chunk_edges"]) for item in job_telemetry), default=0
        )
        max_row = max(
            (int(item["maximum_selected_row_edges"]) for item in job_telemetry), default=0
        )
        phase_seconds = {
            name: sum(float(item[name]) for item in job_telemetry)
            for name in ("direct_seconds", "sparse_seconds", "crosscheck_seconds", "hard_seconds")
        }
        ram_budget = scope.ram_budget_bytes
        peak_rss = memory.get("rss_kib_peak")
        process_swap_growth = memory.get("swap_growth_kib")
        strict_bound_passed = bool(job_telemetry) and max_chunk <= int(args.sparse_max_edges)
        reached_16384 = _DEFAULT_PRODUCT_MAX_SIZE in completed_sizes.get("mv", [])
        persisted_digest_match = (
            None
            if persisted_qualification is None
            else plan.content_digest == persisted_qualification.content_digest
        )
        rss_within_scope_budget = (
            None
            if ram_budget is None or peak_rss is None
            else int(peak_rss) * 1024 <= int(ram_budget)
        )

        total_wall = time.perf_counter() - total_started
        total_usage_after = _usage()
        total_io_after = _proc_io()
        payload = {
            "schema": _RUN_SCHEMA,
            "source": {"git_head": _git_head()},
            "repeat_index": int(args._repeat_index),
            "input": {
                "campaign_config": str(Path(args.campaign_config).expanduser().resolve()),
                "campaign_database": str(database),
                "authority_digests": authority_digests,
                "sparse_index": sparse_counts,
                "requested_scoring_workers": requested_workers,
                "effective_scoring_workers": int(effective_workers),
                "ram_budget_bytes": ram_budget,
                "strict_edge_limit": int(args.sparse_max_edges),
            },
            "authority_load": {
                "wall_seconds": load_wall,
                "wall_hhmmss": format_progress_time(load_wall),
                "resource_delta": _usage_delta(load_usage_before, load_usage_after),
                "proc_io_delta": _dict_delta(load_io_before, load_io_after),
            },
            "mvqual_builder": {
                "wall_seconds": builder_wall,
                "wall_hhmmss": format_progress_time(builder_wall),
                "resource_delta": _usage_delta(builder_usage_before, builder_usage_after),
                "proc_io_delta": _dict_delta(builder_io_before, builder_io_after),
                "system_swap_delta": _dict_delta(swap_before, swap_after),
                "memory": memory,
                "job_count": len(job_telemetry),
                "job_telemetry": job_telemetry,
                "phase_cpu_lane_wall_seconds": phase_seconds,
                "maximum_estimated_job_peak_bytes": 0,
                "maximum_observed_chunk_edges": max_chunk,
                "maximum_selected_row_edges": max_row,
                "completed_rung_sizes": completed_sizes,
            },
            "scientific": {
                "plan_digest": plan.content_digest,
                "outcome": plan.outcome,
                "mv_qualified_sizes": list(plan.mv_qualified_sizes),
                "scientific_validation_passed": True,
                "persisted_qualification_digest_match": persisted_digest_match,
                "scientific_authority_written": False,
            },
            "qualification": {
                "strict_chunk_bound_observed": strict_bound_passed,
                "mv_16384_scored": reached_16384,
                "process_swap_growth_kib": process_swap_growth,
                "no_process_swap_growth": process_swap_growth in (None, 0),
                "peak_rss_within_stage_ram_budget": rss_within_scope_budget,
            },
            "total_execution": {
                "wall_seconds": total_wall,
                "wall_hhmmss": format_progress_time(total_wall),
                "resource_delta": _usage_delta(total_usage_before, total_usage_after),
                "proc_io_delta": _dict_delta(total_io_before, total_io_after),
            },
        }
        _atomic_write_json(Path(args._single_run_output), payload)
        print(
            f"[MVQUAL-MEM1-M5] repeat={args._repeat_index}; "
            f"builder={format_progress_time(builder_wall)}; digest={plan.content_digest[:12]}...; "
            f"peak-rss={memory.get('rss_kib_peak')} KiB; swap-growth={process_swap_growth} KiB",
            flush=True,
        )
        return 0
    finally:
        store.close()

def _product_identity_matches(run: Mapping[str, Any], args: argparse.Namespace) -> bool:
    sparse = run["input"]["sparse_index"]
    domains = sparse["domains"]
    return bool(
        len(domains) == 1
        and int(domains[0]["candidate_count"]) == int(args.expected_candidate_count)
        and int(domains[0]["family_count"]) == int(args.expected_family_count)
        and int(domains[0]["forward_edge_count"]) == int(args.expected_forward_edge_count)
    )


def _aggregate(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    script = Path(__file__).resolve()

    for repeat_index in range(1, int(args.repeats) + 1):
        child_output = output.parent / f".{output.name}.run-{repeat_index}.{os.getpid()}.json"
        command = [
            sys.executable,
            str(script),
            str(Path(args.campaign_config).expanduser().resolve()),
            "--output",
            str(output),
            "--sparse-max-edges",
            str(int(args.sparse_max_edges)),
            "--_single-run-output",
            str(child_output),
            "--_repeat-index",
            str(repeat_index),
        ]
        print(
            f"[MVQUAL-MEM1-M5] repeat={repeat_index}/{args.repeats}; "
            f"timeout={format_progress_time(float(args.timeout_seconds))}; status=starting",
            flush=True,
        )
        try:
            completed = subprocess.run(
                command,
                check=False,
                timeout=float(args.timeout_seconds),
            )
        except subprocess.TimeoutExpired:
            failure = {
                "repeat_index": repeat_index,
                "reason": "timeout",
                "timeout_seconds": float(args.timeout_seconds),
            }
            child_output.unlink(missing_ok=True)
            break
        if completed.returncode != 0:
            failure = {
                "repeat_index": repeat_index,
                "reason": "child_failed",
                "returncode": int(completed.returncode),
            }
            child_output.unlink(missing_ok=True)
            break
        try:
            run = json.loads(child_output.read_text(encoding="utf-8"))
        finally:
            child_output.unlink(missing_ok=True)
        runs.append(run)

    plan_digests = [str(run["scientific"]["plan_digest"]) for run in runs]
    repeated_digest_identical = len(runs) >= 2 and len(set(plan_digests)) == 1
    product_identity = bool(runs) and all(_product_identity_matches(run, args) for run in runs)
    strict_bound = bool(runs) and all(
        bool(run["qualification"]["strict_chunk_bound_observed"]) for run in runs
    )
    max_size_scored = bool(runs) and all(
        int(args.expected_max_size)
        in [int(v) for v in run["mvqual_builder"]["completed_rung_sizes"].get("mv", [])]
        for run in runs
    )
    no_process_swap = bool(runs) and all(
        bool(run["qualification"]["no_process_swap_growth"]) for run in runs
    )
    scientific_valid = bool(runs) and all(
        bool(run["scientific"]["scientific_validation_passed"]) for run in runs
    )
    persisted_matches = [
        run["scientific"].get("persisted_qualification_digest_match") for run in runs
    ]
    no_persisted_regression = all(value is not False for value in persisted_matches)
    source_heads = sorted({str(run["source"]["git_head"]) for run in runs})
    same_source = len(source_heads) == 1
    rss_budget_results = [
        run["qualification"].get("peak_rss_within_stage_ram_budget") for run in runs
    ]

    mechanical_acceptance = bool(
        failure is None
        and len(runs) == int(args.repeats)
        and repeated_digest_identical
        and product_identity
        and strict_bound
        and max_size_scored
        and no_process_swap
        and scientific_valid
        and no_persisted_regression
        and same_source
    )
    payload = {
        "schema": _SCHEMA,
        "source": {"git_heads": source_heads},
        "configuration": {
            "campaign_config": str(Path(args.campaign_config).expanduser().resolve()),
            "repeats": int(args.repeats),
            "timeout_seconds_per_repeat": float(args.timeout_seconds),
            "strict_edge_limit": int(args.sparse_max_edges),
            "expected_product": {
                "candidate_count": int(args.expected_candidate_count),
                "family_count": int(args.expected_family_count),
                "forward_edge_count": int(args.expected_forward_edge_count),
                "maximum_target_size": int(args.expected_max_size),
            },
        },
        "runs": runs,
        "failure": failure,
        "qualification": {
            "completed_repeats": len(runs),
            "repeated_plan_digest_identical": repeated_digest_identical,
            "product_identity_match": product_identity,
            "strict_chunk_bound_observed": strict_bound,
            "full_product_maximum_size_scored": max_size_scored,
            "no_process_swap_growth": no_process_swap,
            "scientific_validation_passed": scientific_valid,
            "persisted_scientific_digest_not_regressed": no_persisted_regression,
            "same_source_commit": same_source,
            "peak_rss_within_stage_ram_budget": rss_budget_results,
            "mechanical_acceptance": mechanical_acceptance,
            "headroom_review_required": True,
            "p0_wall_time_review_required": True,
            "scientific_authority_written": False,
        },
    }
    _atomic_write_json(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    return 0 if mechanical_acceptance else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the M5 bounded-memory MVQUAL product meter from persisted campaign authorities."
        )
    )
    parser.add_argument("campaign_config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--sparse-max-edges", type=int, default=_DEFAULT_STRICT_EDGES)
    parser.add_argument(
        "--expected-candidate-count", type=int, default=_DEFAULT_PRODUCT_CANDIDATES
    )
    parser.add_argument("--expected-family-count", type=int, default=_DEFAULT_PRODUCT_FAMILIES)
    parser.add_argument(
        "--expected-forward-edge-count", type=int, default=_DEFAULT_PRODUCT_FORWARD_EDGES
    )
    parser.add_argument("--expected-max-size", type=int, default=_DEFAULT_PRODUCT_MAX_SIZE)
    parser.add_argument("--_single-run-output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--_repeat-index", type=int, default=1, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if int(args.repeats) < 2 and args._single_run_output is None:
        raise SystemExit("M5 requires at least two repetitions to prove digest determinism")
    if float(args.timeout_seconds) <= 0.0:
        raise SystemExit("--timeout-seconds must be positive")
    if int(args.sparse_max_edges) < 1:
        raise SystemExit("--sparse-max-edges must be positive")
    if args._single_run_output is not None:
        return _single_run(args)
    return _aggregate(args)


if __name__ == "__main__":
    raise SystemExit(main())
