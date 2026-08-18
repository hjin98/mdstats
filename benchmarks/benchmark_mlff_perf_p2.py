#!/usr/bin/env python3
"""Qualify PERF-P2 lazy TARGET-DATA2C v2 against the exhaustive v1 oracle."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Sequence

import numpy as np

import mdstats
from mdstats.training_data import target_ladder as tl
from mdstats.training_data._common import canonical_json, digest

SCHEMA = "mdstats.mlff-perf-p2-benchmark.v1"


@dataclass(slots=True)
class Measurement:
    wall_seconds: float
    process_cpu_seconds: float
    rss_start_mib: float
    rss_end_mib: float
    rss_peak_mib: float
    rss_increment_mib: float


class _RssMonitor:
    def __init__(self, period_seconds: float = 0.005) -> None:
        self.period_seconds = period_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.start = self.end = self.peak = 0

    @staticmethod
    def current_bytes() -> int:
        try:
            for line in Path("/proc/self/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        except OSError:
            pass
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024

    def __enter__(self) -> "_RssMonitor":
        self.start = self.current_bytes()
        self.peak = self.start
        def sample() -> None:
            while not self._stop.wait(self.period_seconds):
                self.peak = max(self.peak, self.current_bytes())
        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.end = self.current_bytes()
        self.peak = max(self.peak, self.end)
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def result(self, wall: float, cpu: float) -> Measurement:
        mib = 1024.0 * 1024.0
        return Measurement(
            wall_seconds=wall,
            process_cpu_seconds=cpu,
            rss_start_mib=self.start / mib,
            rss_end_mib=self.end / mib,
            rss_peak_mib=self.peak / mib,
            rss_increment_mib=max(0, self.peak - self.start) / mib,
        )


def _measure(fn: Callable[[], Any]) -> tuple[Any, Measurement]:
    with _RssMonitor() as monitor:
        w0 = time.perf_counter(); c0 = time.process_time()
        value = fn()
        cpu = time.process_time() - c0; wall = time.perf_counter() - w0
    return value, monitor.result(wall, cpu)


def _stats(items: Sequence[Measurement]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name in ("wall_seconds", "process_cpu_seconds", "rss_peak_mib", "rss_increment_mib"):
        values = np.asarray([getattr(item, name) for item in items], dtype=np.float64)
        out[name] = {"min": float(np.min(values)), "median": float(np.median(values)), "max": float(np.max(values))}
    return out


def _host() -> dict[str, Any]:
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip(); break
    except OSError:
        pass
    def read(path: str) -> str | None:
        try: return Path(path).read_text().strip()
        except OSError: return None
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_model": cpu,
        "logical_cpus": os.cpu_count(),
        "cgroup_cpu_max": read("/sys/fs/cgroup/cpu.max"),
        "cgroup_memory_max": read("/sys/fs/cgroup/memory.max"),
        "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
    }


class _RoleDomain:
    def __init__(self, domain: Any) -> None:
        self.label_domain_id = domain.label_domain_id
        self.size_development_frame_uids = tuple(domain.frame_uids)
        self.development_intervals = ()
        self.content_digest = digest({"perf_p2_role_domain": self.label_domain_id, "frames": self.size_development_frame_uids})


class _RoleFreeze:
    def __init__(self, reference: mdstats.TargetCoverageReference) -> None:
        self.dataset_id = reference.dataset_id
        self.content_digest = reference.target_data_role_freeze_digest
        self.domains = tuple(_RoleDomain(domain) for domain in reference.domains)
        self._by_id = {item.label_domain_id: item for item in self.domains}

    def domain(self, label_domain_id: str) -> _RoleDomain:
        return self._by_id[label_domain_id]


def _canonicalize_reference(reference: mdstats.TargetCoverageReference, *, permissive: bool) -> mdstats.TargetCoverageReference:
    """Remap frame indices to the DATA2C role-order contract without changing rows."""
    domains = []
    for domain in reference.domains:
        ordered_uids = tuple(sorted(domain.frame_uids))
        new_index = {uid: index for index, uid in enumerate(ordered_uids)}
        families = []
        for family in domain.families:
            indices = np.asarray(
                [new_index[domain.frame_uids[int(index)]] for index in family.frame_indices],
                dtype=np.int64,
            )
            kwargs: dict[str, Any] = {"frame_indices": indices}
            if permissive:
                kwargs.update(local_radii=np.full_like(family.local_radii, 1.0e9), extent_channels=())
            families.append(replace(family, **kwargs))
        strata = () if permissive else tuple(
            replace(
                stratum,
                frame_indices=tuple(sorted(new_index[domain.frame_uids[int(index)]] for index in stratum.frame_indices)),
            )
            for stratum in domain.strata
        )
        domains.append(replace(
            domain,
            frame_uids=ordered_uids,
            families=tuple(families),
            strata=strata,
            frame_domain_digest=digest({"perf_p2_canonical_frame_domain": ordered_uids}),
        ))
    return replace(reference, domains=tuple(domains))


def _load_case(p0_evidence: Path, reference_root: Path, case: str):
    p0 = json.loads(p0_evidence.read_text())
    pointer = p0["persistence"]["native_v2"]["pointer"]
    source = mdstats.read_target_coverage_native_record(pointer, reference_root, mmap_threshold_bytes=0)
    reference = _canonicalize_reference(source, permissive=(case == "early_stop"))
    role = _RoleFreeze(reference)
    policy = mdstats.TargetDataLadderPolicy(
        reserve_required_strata=False,
        reserve_correlation_intervals=False,
    )
    return source, reference, role, policy


def _build(mode: str, reference, role, policy, workers: int):
    if mode == "v1":
        return tl._build_target_data_ladder_exhaustive_v1(
            reference, role, policy=policy, coverage_query_workers=workers
        )
    return mdstats.build_target_data_ladder(
        reference,
        role,
        policy=policy,
        coverage_query_workers=workers,
        stage_a_survivor_limit=4,
    )


def _rung_map(plan: mdstats.TargetDataLadderPlan) -> dict[tuple[str, int], mdstats.TargetDataLadderRung]:
    return {
        (domain.label_domain_id, rung.target_size): rung
        for domain in plan.domains
        for rung in domain.materialized_rungs
    }


def _equivalence(v1: mdstats.TargetDataLadderPlan, v2: mdstats.TargetDataLadderPlan) -> dict[str, Any]:
    c1 = mdstats.build_target_size_convergence_plan(v1)
    c2 = mdstats.build_target_size_convergence_plan(v2)
    survivors = c1.stage_a_survivor_sizes
    m1 = _rung_map(v1); m2 = _rung_map(v2)
    membership_exact = True; report_exact = True; mandatory_exact = True
    survivor_digests: dict[str, Any] = {}
    for domain in v2.domains:
        for size in survivors:
            a = m1[(domain.label_domain_id, size)]; b = m2[(domain.label_domain_id, size)]
            membership_exact &= a.frame_uids == b.frame_uids
            mandatory_exact &= (
                a.mandatory_obligations_passed == b.mandatory_obligations_passed
                and a.unsatisfied_obligation_ids == b.unsatisfied_obligation_ids
            )
            assert a.coverage_report is not None and b.coverage_report is not None
            report_exact &= a.coverage_report.content_digest == b.coverage_report.content_digest
            survivor_digests[f"{domain.label_domain_id}:{size}"] = {
                "membership_digest": digest({"frame_uids": b.frame_uids}),
                "coverage_report_digest": b.coverage_report.content_digest,
                "coverage_passed": b.coverage_report.passed,
            }
    return {
        "v1_stage_a_survivor_sizes": list(c1.stage_a_survivor_sizes),
        "v2_stage_a_survivor_sizes": list(c2.stage_a_survivor_sizes),
        "stage_a_survivor_sizes_exact": c1.stage_a_survivor_sizes == c2.stage_a_survivor_sizes,
        "survivor_membership_exact": membership_exact,
        "survivor_coverage_report_exact": report_exact,
        "survivor_mandatory_status_exact": mandatory_exact,
        "survivor_digests": survivor_digests,
    }


def _plan_structure(plan: mdstats.TargetDataLadderPlan) -> dict[str, Any]:
    return {
        "authority_version": plan.authority_version,
        "content_digest": plan.content_digest,
        "materialized_target_sizes": list(plan.materialized_target_sizes) if plan.authority_version == mdstats.TARGET_DATA_LADDER_VERSION else [r.target_size for r in plan.domains[0].materialized_rungs],
        "intentionally_unmaterialized_target_sizes": list(plan.intentionally_unmaterialized_target_sizes),
        "master_order_entries": sum(len(domain.master_order) for domain in plan.domains),
        "materialized_rung_records": sum(len(domain.materialized_rungs) for domain in plan.domains),
        "serialized_json_bytes": len(canonical_json(plan.to_dict()).encode("utf-8")),
    }


def _scientific_signature(plan: mdstats.TargetDataLadderPlan) -> dict[str, Any]:
    convergence = mdstats.build_target_size_convergence_plan(plan)
    survivors = convergence.stage_a_survivor_sizes
    rung_map = _rung_map(plan)
    evidence: dict[str, Any] = {}
    for domain in plan.domains:
        for size in survivors:
            rung = rung_map[(domain.label_domain_id, size)]
            assert rung.coverage_report is not None
            evidence[f"{domain.label_domain_id}:{size}"] = {
                "membership_digest": digest({"frame_uids": rung.frame_uids}),
                "coverage_report_digest": rung.coverage_report.content_digest,
                "coverage_passed": rung.coverage_report.passed,
                "mandatory_obligations_passed": rung.mandatory_obligations_passed,
                "unsatisfied_obligation_ids": list(rung.unsatisfied_obligation_ids),
            }
    return {
        "stage_a_survivor_sizes": list(survivors),
        "survivor_evidence": evidence,
        "signature_digest": digest({"survivor_sizes": survivors, "evidence": evidence}),
    }


def _child(args: argparse.Namespace) -> None:
    _, reference, role, policy = _load_case(args.p0_evidence, args.reference_root, args.child_case)
    w0 = time.perf_counter(); c0 = time.process_time()
    plan = _build(args.child_mode, reference, role, policy, args.workers)
    payload = {
        "case": args.child_case,
        "mode": args.child_mode,
        "workers": args.workers,
        "wall_seconds": time.perf_counter() - w0,
        "process_cpu_seconds": time.process_time() - c0,
        "ru_maxrss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        "structure": _plan_structure(plan),
        "scientific_signature": _scientific_signature(plan),
    }
    print(json.dumps(payload, sort_keys=True))


def _run_child(case: str, mode: str, args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable, __file__,
        "--p0-evidence", str(args.p0_evidence),
        "--reference-root", str(args.reference_root),
        "--workers", str(args.workers),
        "--child-case", case,
        "--child-mode", mode,
    ]
    proc = subprocess.run(command, check=True, capture_output=True, text=True, env=os.environ.copy())
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p0-evidence", type=Path, default=Path("/mnt/data/mdstats_release_179/mlff_perf_p0_lta_cloud_cpu_2026-08-15.json"))
    parser.add_argument("--reference-root", type=Path, default=Path("/mnt/data/mdstats_perf_p0/persistence_stages"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--child-case", choices=("fallback", "early_stop"))
    parser.add_argument("--child-mode", choices=("v1", "v2"))
    args = parser.parse_args()
    if args.child_case:
        if args.child_mode is None:
            parser.error("--child-mode is required with --child-case")
        _child(args); return

    repeats = max(1, int(args.repeats)); workers = max(1, int(args.workers))
    p0 = json.loads(args.p0_evidence.read_text())
    pointer = p0["persistence"]["native_v2"]["pointer"]
    source_identity = {
        "content_digest": pointer["content_digest"],
        "frame_count": int(p0["target_frames"]),
        "domain_ids": ["lta-target"],
    }
    cases: dict[str, Any] = {}
    for case in ("fallback", "early_stop"):
        samples: dict[str, list[dict[str, Any]]] = {"v1": [], "v2": []}
        for rep in range(repeats):
            modes = ("v1", "v2") if rep % 2 == 0 else ("v2", "v1")
            for mode in modes:
                samples[mode].append(_run_child(case, mode, args))
        v1_ref = samples["v1"][0]
        v2_ref = samples["v2"][0]
        for mode in ("v1", "v2"):
            reference_signature = samples[mode][0]["scientific_signature"]["signature_digest"]
            reference_plan = samples[mode][0]["structure"]["content_digest"]
            if any(item["scientific_signature"]["signature_digest"] != reference_signature for item in samples[mode]):
                raise RuntimeError(f"{case} {mode} scientific signature changed across fresh-process repeats")
            if any(item["structure"]["content_digest"] != reference_plan for item in samples[mode]):
                raise RuntimeError(f"{case} {mode} plan digest changed across fresh-process repeats")
        s1 = v1_ref["scientific_signature"]; s2 = v2_ref["scientific_signature"]
        equivalence = {
            "v1_stage_a_survivor_sizes": s1["stage_a_survivor_sizes"],
            "v2_stage_a_survivor_sizes": s2["stage_a_survivor_sizes"],
            "stage_a_survivor_sizes_exact": s1["stage_a_survivor_sizes"] == s2["stage_a_survivor_sizes"],
            "survivor_evidence_exact": s1["survivor_evidence"] == s2["survivor_evidence"],
            "v1_signature_digest": s1["signature_digest"],
            "v2_signature_digest": s2["signature_digest"],
        }
        def fresh_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
            result: dict[str, dict[str, float]] = {}
            for field in ("wall_seconds", "process_cpu_seconds", "ru_maxrss_mib"):
                values = np.asarray([float(row[field]) for row in rows], dtype=np.float64)
                result[field] = {"min": float(np.min(values)), "median": float(np.median(values)), "max": float(np.max(values))}
            return result
        cases[case] = {
            "equivalence": equivalence,
            "v1_structure": v1_ref["structure"],
            "v2_structure": v2_ref["structure"],
            "v1_samples": samples["v1"],
            "v2_samples": samples["v2"],
            "v1_summary": fresh_stats(samples["v1"]),
            "v2_summary": fresh_stats(samples["v2"]),
            "fixture_note": (
                "P0 native reference remapped to lexicographic frame-index authority; original coverage radii/extents retained."
                if case == "fallback" else
                "Same remapped P0 reference with qualification-only permissive local radii and no extent channels, forcing the monotone early-stop branch."
            ),
        }

    # Worker count is execution-only; compare fresh-process v2 authorities.
    worker_args = argparse.Namespace(**vars(args)); worker_args.workers = 1
    worker_one = _run_child("early_stop", "v2", worker_args)
    worker_many = _run_child("early_stop", "v2", args)
    worker_invariance = {
        "workers_a": 1,
        "workers_b": workers,
        "plan_content_digest_a": worker_one["structure"]["content_digest"],
        "plan_content_digest_b": worker_many["structure"]["content_digest"],
        "scientific_signature_a": worker_one["scientific_signature"]["signature_digest"],
        "scientific_signature_b": worker_many["scientific_signature"]["signature_digest"],
        "exact": (
            worker_one["structure"]["content_digest"] == worker_many["structure"]["content_digest"]
            and worker_one["scientific_signature"]["signature_digest"] == worker_many["scientific_signature"]["signature_digest"]
        ),
    }
    scientific = {
        "source_perf_p0_reference": source_identity,
        "cases": {
            name: {
                "equivalence": value["equivalence"],
                "v1_structure": value["v1_structure"],
                "v2_structure": value["v2_structure"],
            } for name, value in cases.items()
        },
        "worker_invariance": worker_invariance,
    }
    execution = {
        "host": _host(),
        "repeats": repeats,
        "coverage_query_workers": workers,
        "measurement_isolation": "fresh_process_per_sample",
        "cases": {
            name: {
                "fixture_note": value["fixture_note"],
                "v1_samples": value["v1_samples"],
                "v2_samples": value["v2_samples"],
                "v1_summary": value["v1_summary"],
                "v2_summary": value["v2_summary"],
            } for name, value in cases.items()
        },
    }
    payload = {
        "schema": SCHEMA,
        "source_version": mdstats.__version__,
        "scientific": scientific,
        "execution": execution,
    }
    payload["scientific_digest"] = digest(scientific)
    payload["execution_digest"] = digest(execution)
    payload["content_digest"] = digest({
        "schema": SCHEMA,
        "source_version": mdstats.__version__,
        "scientific_digest": payload["scientific_digest"],
        "execution_digest": payload["execution_digest"],
    })
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(canonical_json(payload) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
