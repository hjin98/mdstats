#!/usr/bin/env python3
"""PERFBASE1 repeated exact-equivalence CPU baseline suite.

The suite runs each workload schedule/repeat sweep in one controlled child process.
Process startup/import cost stays outside every trial meter. Supplied
LTA target labels are parsed once into a deterministic family cache; the timed
TARGET-DATA2B workload then measures only the exact reference-radius kernel.
The replay workload uses the current unified 12,000-frame ExtXYZ source.  FEAS1,
MVIDX1, and MVSEL1 use deterministic synthetic sparse/neighborhood workloads so
later algorithmic scaling changes can be compared independent of XML/model I/O.

The active foundation checkpoint is authenticated and recorded but model
inference is not fabricated on hosts lacking the MACE runtime/GPU.  Foundation
family/variant are CLI inputs, so the same baseline authority supports MPA-0
and MH-1.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import numpy as np
from ase.io import iread

import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.performance_baseline import PerfBase0ArtifactIdentity
from mdstats.training_data.perfbase1 import (
    PerfBase1Record,
    PerfBase1Trial,
    PerfBase1TrialMeter,
    PerfBase1Workload,
    render_perfbase1_markdown,
    write_perfbase1_record,
)
from mdstats.training_data.resources import detect_system_resources
from mdstats.training_data import target_coverage as tc


SUITE_POLICY = {
    "schema": "mdstats.mlff-perfbase1-benchmark-policy.v1",
    "worker_schedule": "serial,dual,bounded-intermediate,automatic-budget",
    "trial_isolation": "one controlled benchmark process; stage-local meters exclude deterministic fixture preparation",
    "native_thread_policy": "OMP/MKL/OpenBLAS/NumExpr/BLIS/vecLib=1 except explicit cKDTree query workers",
    "target_radius_block_size": 1024,
    "coverage_beta": 1.0 / 128.0,
    "coverage_leave_one_out": True,
    "synthetic_candidate_count": 8192,
    "synthetic_family_count": 6,
    "synthetic_query_block_size": 512,
    "mvsel_candidate_count": 8192,
    "mvsel_selection_count": 4096,
    "mvsel_degree": 16,
    "mvsel_family_count": 3,
}
SUITE_POLICY_DIGEST = digest(SUITE_POLICY)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _prepare_target_cache(training_root: Path, cache: Path) -> dict[str, Any]:
    # Reuse the frozen PERF-BASE0 supplied-data feature/family extraction so the
    # new gate measures the current exact radius kernel over the same realistic
    # label/cell/species family geometry without redefining its scientific input.
    from benchmark_mlff_perf_base0 import ingest_training, build_realistic_families

    all_paths = tuple(sorted(training_root.glob("*.xml")))
    if len(all_paths) != 27:
        raise SystemExit(f"PERFBASE1 expected 27 target XML files, found {len(all_paths)}.")
    # PERFBASE1 needs a reproducible supplied-data workload, not another full
    # campaign ingestion pass.  Use a fixed, composition-complete LTA subset
    # spanning low/high temperature and hydrostatic strain; authenticate the
    # complete source archive separately in the top-level record.
    selected_names = (
        "LTA_LiNaK.300K.init.xml",
        "LTA_LiNaK.800K.init.xml",
        "LTA_LiNaK_strained.hydro+0.05.init.xml",
    )
    by_name = {path.name: path for path in all_paths}
    paths = tuple(by_name[name] for name in selected_names)
    training = ingest_training(paths, training_root)
    families = build_realistic_families(training, workers=1, block_size=1024)
    payload: dict[str, np.ndarray] = {}
    catalog = []
    for i, family in enumerate(families):
        payload[f"scaled_{i}"] = np.asarray(family.scaled, dtype=np.float64)
        payload[f"weights_{i}"] = np.asarray(family.weights, dtype=np.float64)
        catalog.append({
            "index": i,
            "family_id": family.family_id,
            "element_count": int(family.scaled.shape[0]),
            "feature_count": int(family.scaled.shape[1]),
        })
    payload["catalog_json"] = np.asarray(json.dumps(catalog, sort_keys=True))
    payload["frame_count"] = np.asarray(len(training.frame_uids), dtype=np.int64)
    payload["atom_count"] = np.asarray(training.atom_count, dtype=np.int64)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, **payload)
    return {
        "frame_count": len(training.frame_uids),
        "atom_count": training.atom_count,
        "family_count": len(families),
        "family_element_count": sum(int(f.scaled.shape[0]) for f in families),
        "selected_source_files": list(selected_names),
        "complete_source_file_count": len(all_paths),
        "cache_sha256": _sha256(cache),
        "catalog": catalog,
    }


def _target_radii_worker(args: argparse.Namespace) -> PerfBase1Trial:
    from mdstats.training_data.target_coverage import _local_reference_radii

    with np.load(args.target_cache, allow_pickle=False) as data:
        catalog = json.loads(str(data["catalog_json"].item()))
        arrays = [
            (np.asarray(data[f"scaled_{i}"], dtype=np.float64), np.asarray(data[f"weights_{i}"], dtype=np.float64))
            for i in range(len(catalog))
        ]
    outputs: list[np.ndarray] = []
    temp = max((x.nbytes + w.nbytes for x, w in arrays), default=0)
    with PerfBase1TrialMeter(
        "target_data2b_reference_radii",
        schedule_label=args.schedule_label,
        repeat_index=args.repeat_index,
        requested_workers=args.workers,
        allocated_workers=args.workers,
        worker_settings={"ckdtree_query_workers": args.workers, "row_block_size": 1024},
    ) as meter:
        for values, weights in arrays:
            outputs.append(_local_reference_radii(
                values, weights, beta=1.0 / 128.0, leave_one_out=True,
                block_size=1024, query_workers=args.workers,
            ))
    output_digest = digest([
        hashlib.sha256(np.ascontiguousarray(a, dtype="<f8").tobytes()).hexdigest() for a in outputs
    ])
    return meter.trial(
        scientific_output_digest=output_digest,
        throughput_count=sum(a.size for a in outputs),
        throughput_unit="family-elements",
        temporary_array_bytes=temp,
        counters={"family_count": len(outputs), "family_elements": sum(a.size for a in outputs)},
        events=("Current serial family/block driver; explicit native cKDTree worker count.",),
    )


class _Unit:
    def __init__(self, unit_id: str): self.unit_id = unit_id
class _UnitCatalog:
    def __init__(self, mapping: dict[str, str]): self.mapping = mapping
    def unit_for_frame(self, frame_uid: str) -> _Unit: return _Unit(self.mapping[frame_uid])
class _Data5:
    def __init__(self, mapping: dict[str, str]): self.unit_catalog = _UnitCatalog(mapping)
@dataclass(frozen=True)
class _Interval:
    unit_id: str
    frame_uids: tuple[str, ...]
class _RoleDomain:
    def __init__(self, frame_uids: tuple[str, ...], intervals: tuple[_Interval, ...]):
        self.label_domain_id = "target"
        self.size_development_frame_uids = frame_uids
        self.development_intervals = intervals
class _RoleFreeze:
    def __init__(self, domain: _RoleDomain, content_digest: str):
        self.dataset_id = "perfbase1-synthetic"
        self.content_digest = content_digest
        self._domain = domain
    def domain(self, label_domain_id: str):
        if label_domain_id != "target": raise KeyError(label_domain_id)
        return self._domain


_SYNTHETIC_AUTHORITY_CACHE: tuple[Any, Any] | None = None
_SYNTHETIC_FEASIBILITY_CACHE: Any | None = None

def _synthetic_reference(n: int = 8192, family_count: int = 6):
    frame_uids = tuple(hashlib.sha256(f"perfbase1-{i:08d}".encode()).hexdigest() for i in range(n))
    unit_count = max(16, n // 128)
    mapping = {uid: f"unit-{i % unit_count:04d}" for i, uid in enumerate(frame_uids)}
    data5 = _Data5(mapping)
    policy = mdstats.TargetCoveragePolicy(
        coverage_resolution_mass=1.0 / 128.0,
        coverage_threshold=0.95,
        require_condition_support=False,
        require_structural_event_support=False,
        require_profile_environment_support=False,
    )
    domain_index = {uid: i for i, uid in enumerate(frame_uids)}
    x = np.arange(n, dtype=np.float64)
    families = []
    for family_index in range(family_count):
        phase = family_index + 1.0
        values = np.column_stack((
            np.sin((x + phase) * 0.017),
            np.cos((x * (family_index + 2) + phase) * 0.011),
            ((x * (2 * family_index + 3)) % 997.0) / 997.0,
        ))
        family = tc._build_family(
            family_id=f"target_label:perfbase1-{family_index}",
            family_kind="target_label",
            semantic_family=f"perfbase1-{family_index}",
            feature_names=("x", "y", "z"),
            frame_uids=frame_uids,
            values=values,
            domain_frame_index=domain_index,
            data5_bundle=data5,
            policy=policy,
            source_evidence_digest=hashlib.sha256(f"family-{family_index}".encode()).hexdigest(),
            required=True,
            extent=False,
            query_workers=1,
            radius_block_size=1024,
        )
        assert family is not None
        families.append(family)
    domain = mdstats.TargetCoverageDomainReference(
        label_domain_id="target",
        frame_uids=frame_uids,
        families=tuple(families),
        strata=(),
        frame_domain_digest="b" * 64,
    )
    role_digest = "6" * 64
    reference = mdstats.TargetCoverageReference(
        dataset_id="perfbase1-synthetic",
        source_catalog_digest="1" * 64,
        frame_catalog_digest="2" * 64,
        data4_bundle_digest="3" * 64,
        data5_bundle_digest="4" * 64,
        data6_bundle_digest="5" * 64,
        target_data_role_freeze_digest=role_digest,
        foundation_target_audit_digest="7" * 64,
        policy=policy,
        domains=(domain,),
    )
    by_unit: dict[str, list[str]] = {}
    for uid, unit in mapping.items(): by_unit.setdefault(unit, []).append(uid)
    intervals = tuple(
        _Interval(unit_id=hashlib.sha256(name.encode()).hexdigest(), frame_uids=tuple(uids))
        for name, uids in sorted(by_unit.items())
    )
    return reference, _RoleFreeze(_RoleDomain(frame_uids, intervals), role_digest)


_BUSY_RE = re.compile(r"workers-busy=(\d+)/(\d+); pending=(\d+); queued=(\d+)")

def _queue_summary(messages: list[str]) -> dict[str, Any]:
    samples = []
    for message in messages:
        match = _BUSY_RE.search(message)
        if match:
            samples.append(tuple(int(x) for x in match.groups()))
    if not samples:
        return {"observed": False, "progress_messages": len(messages), "sample_count": 0}
    arr = np.asarray(samples, dtype=np.float64)
    return {
        "observed": True,
        "progress_messages": len(messages),
        "sample_count": len(samples),
        "mean_busy_workers": float(np.mean(arr[:, 0])),
        "max_busy_workers": int(np.max(arr[:, 0])),
        "worker_capacity": int(np.max(arr[:, 1])),
        "mean_pending_tasks": float(np.mean(arr[:, 2])),
        "max_pending_tasks": int(np.max(arr[:, 2])),
        "mean_queued_tasks": float(np.mean(arr[:, 3])),
        "max_queued_tasks": int(np.max(arr[:, 3])),
    }


def _get_synthetic_authorities():
    global _SYNTHETIC_AUTHORITY_CACHE
    if _SYNTHETIC_AUTHORITY_CACHE is None:
        _SYNTHETIC_AUTHORITY_CACHE = _synthetic_reference()
    return _SYNTHETIC_AUTHORITY_CACHE

def _get_serial_feasibility(reference, role):
    global _SYNTHETIC_FEASIBILITY_CACHE
    if _SYNTHETIC_FEASIBILITY_CACHE is None:
        _SYNTHETIC_FEASIBILITY_CACHE = mdstats.build_target_coverage_feasibility_report(
            reference, role, query_workers=1, query_block_size=512, block_workers=1
        )
    return _SYNTHETIC_FEASIBILITY_CACHE

def _feas1_worker(args: argparse.Namespace) -> PerfBase1Trial:
    reference, role = _get_synthetic_authorities()
    messages: list[str] = []
    with PerfBase1TrialMeter(
        "target_data2b_feas1",
        schedule_label=args.schedule_label,
        repeat_index=args.repeat_index,
        requested_workers=args.workers,
        allocated_workers=args.workers,
        worker_settings={"global_workers": args.workers, "tree_workers_per_task": 1, "query_block_size": 512, "scheduler": "parcore1"},
    ) as meter:
        report = mdstats.build_target_coverage_feasibility_report(
            reference, role, query_workers=1, query_block_size=512,
            block_workers=args.workers, progress_interval_seconds=0.02,
            progress_callback=messages.append,
        )
    edges = sum(f.neighborhood_edge_count for d in report.domains for f in d.family_reports)
    witnesses = sum(f.witness_count for d in report.domains for f in d.family_reports)
    return meter.trial(
        scientific_output_digest=report.content_digest,
        throughput_count=witnesses,
        throughput_unit="witnesses",
        persisted_bytes=len(json.dumps(report.to_dict(), sort_keys=True).encode()),
        counters={"profiles": sum(len(d.family_reports) for d in report.domains), "witnesses": witnesses, "edges": edges},
        queue=_queue_summary(messages),
        events=("PARCORE1 shared deterministic FEAS1 queue; cKDTree workers=1/task.",),
    )


def _mvidx1_worker(args: argparse.Namespace) -> PerfBase1Trial:
    reference, role = _get_synthetic_authorities()
    feasibility = _get_serial_feasibility(reference, role)
    messages: list[str] = []
    with PerfBase1TrialMeter(
        "target_data2c_mvidx1",
        schedule_label=args.schedule_label,
        repeat_index=args.repeat_index,
        requested_workers=args.workers,
        allocated_workers=args.workers,
        worker_settings={"ckdtree_query_workers": args.workers, "query_block_size": 512},
    ) as meter:
        index = mdstats.build_target_coverage_sparse_index(
            reference, role, feasibility, query_workers=args.workers,
            query_block_size=512, progress_interval_seconds=0.02,
            progress_callback=messages.append,
        )
    edges = sum(f.edge_count for d in index.domains for f in d.families)
    return meter.trial(
        scientific_output_digest=index.content_digest,
        throughput_count=edges,
        throughput_unit="edges",
        persisted_bytes=len(json.dumps(index.to_dict(), sort_keys=True).encode()),
        counters={"families": sum(len(d.families) for d in index.domains), "edges": edges, "progress_messages": len(messages)},
        queue={"observed": False, "progress_messages": len(messages)},
        events=("Current MVIDX1 repeats exact geometry sweep; native cKDTree workers vary by schedule.",),
    )


class _SparseFamily:
    def __init__(self, family_id: str, n: int, degree: int, stride: int) -> None:
        self.family_id = family_id
        self.candidate_count = n
        self.witness_count = n
        base = np.arange(n, dtype=np.uint32)
        rows = np.empty((n, degree), dtype=np.uint32)
        for j in range(degree):
            rows[:, j] = (base + j * (2 * stride + 1)) % n
        rows.sort(axis=1)
        self.candidate_offsets = np.arange(0, (n + 1) * degree, degree, dtype=np.uint64)
        self.candidate_witnesses = rows.ravel()
        counts = np.bincount(self.candidate_witnesses.astype(np.int64), minlength=n)
        self.witness_offsets = np.empty(n + 1, dtype=np.uint64)
        self.witness_offsets[0] = 0
        np.cumsum(counts, dtype=np.int64, out=self.witness_offsets[1:])
        self.witness_candidates = np.empty(n * degree, dtype=np.uint32)
        cursor = self.witness_offsets[:-1].copy()
        for candidate in range(n):
            for witness in rows[candidate]:
                position = int(cursor[witness])
                self.witness_candidates[position] = candidate
                cursor[witness] += 1
        for witness in range(n):
            start, stop = int(self.witness_offsets[witness]), int(self.witness_offsets[witness + 1])
            self.witness_candidates[start:stop].sort()
    def candidate_witness_indices(self, candidate: int) -> np.ndarray:
        start, stop = int(self.candidate_offsets[candidate]), int(self.candidate_offsets[candidate + 1])
        return self.candidate_witnesses[start:stop]
    def witness_candidate_indices(self, witness: int) -> np.ndarray:
        start, stop = int(self.witness_offsets[witness]), int(self.witness_offsets[witness + 1])
        return self.witness_candidates[start:stop]
class _ReferenceFamily:
    def __init__(self, family_id: str, n: int, phase: float) -> None:
        self.family_id = family_id
        x = np.arange(n, dtype=np.float64)
        weights = 1.0 + ((x * 0.6180339887498949 + phase) % 1.0)
        self.weights = weights / np.sum(weights, dtype=np.float64)
class _ReferenceDomain:
    label_domain_id = "mvperf1"
    content_digest = "a" * 64
    frame_domain_digest = "b" * 64
    def __init__(self, n: int, families: tuple[_SparseFamily, ...]) -> None:
        self.frame_uids = tuple(hashlib.sha256(f"mvperf1-frame-{i:08d}".encode()).hexdigest() for i in range(n))
        self._families = {f.family_id: _ReferenceFamily(f.family_id, n, i / 11.0) for i, f in enumerate(families)}
    def family(self, family_id: str) -> _ReferenceFamily: return self._families[family_id]
class _SparseDomain:
    content_digest = "c" * 64
    frame_domain_digest = "b" * 64
    obligations: tuple[Any, ...] = ()
    def __init__(self, n: int, families: tuple[_SparseFamily, ...]) -> None:
        self.candidate_count = n
        self.families = families
        unit_count = max(1, n // 32)
        self.correlation_unit_ids = tuple(str(i) for i in range(unit_count))
        self.candidate_correlation_unit_codes = np.arange(n, dtype=np.int32) % unit_count
    def candidate_obligation_indices(self, candidate: int) -> np.ndarray: return np.empty(0, dtype=np.uint32)
    def obligation_candidate_indices(self, obligation: int) -> np.ndarray: return np.empty(0, dtype=np.uint32)


def _mvsel1_worker(args: argparse.Namespace) -> PerfBase1Trial:
    from mdstats.training_data import target_multi_view_selector as mvsel
    n = 8192; k = 4096; degree = 16; family_count = 3
    families = tuple(_SparseFamily(f"family_{i}", n, degree, 2 * i + 1) for i in range(family_count))
    reference = _ReferenceDomain(n, families)
    sparse = _SparseDomain(n, families)
    policy = mvsel.TargetMultiViewSelectorPolicy(target_sizes=(k,))
    state = mvsel._build_domain_state(reference, sparse)
    selected: list[int] = []
    # MVSEL rank authority is deliberately sequential; requested worker count is
    # recorded while actual allocated lanes remain one.
    with PerfBase1TrialMeter(
        "target_data2c_mvsel1_kernel",
        schedule_label=args.schedule_label,
        repeat_index=args.repeat_index,
        requested_workers=args.workers,
        allocated_workers=1,
        worker_settings={"requested_stage_workers": args.workers, "sequential_rank_authority": True},
    ) as meter:
        for _ in range(k):
            candidate, _, _, _ = mvsel._choose_candidate(reference, sparse, state, policy)
            selected.append(candidate)
            mvsel._select_and_update(candidate, sparse, state)
    output_digest = hashlib.sha256(np.asarray(selected, dtype="<u4").tobytes()).hexdigest()
    return meter.trial(
        scientific_output_digest=output_digest,
        throughput_count=k,
        throughput_unit="selected-ranks",
        counters={"candidate_count": n, "selected_count": k, "edge_count": n * degree * family_count},
        events=("Sequential rank authority; baseline exposes sparse Python/update cost rather than fake outer parallelism.",),
    )


def _replay_worker(args: argparse.Namespace) -> PerfBase1Trial:
    frame_count = atom_count = 0
    digest_hasher = hashlib.sha256()
    # Current replay ingest is serial.  Requested schedule is retained as a
    # diagnostic, but actual allocated lanes are one.
    with PerfBase1TrialMeter(
        "replay_unified_extxyz_ingest",
        schedule_label=args.schedule_label,
        repeat_index=args.repeat_index,
        requested_workers=args.workers,
        allocated_workers=1,
        worker_settings={"requested_stage_workers": args.workers, "parser_workers": 1},
    ) as meter:
        for atoms in iread(args.replay, index=":", format="extxyz"):
            frame_count += 1
            atom_count += len(atoms)
            digest_hasher.update(np.asarray(atoms.numbers, dtype="<i4").tobytes())
            digest_hasher.update(np.asarray(atoms.positions, dtype="<f8").tobytes())
            digest_hasher.update(np.asarray(atoms.cell.array, dtype="<f8").tobytes())
            digest_hasher.update(np.asarray(atoms.pbc, dtype=np.uint8).tobytes())
    return meter.trial(
        scientific_output_digest=digest_hasher.hexdigest(),
        throughput_count=frame_count,
        throughput_unit="frames",
        counters={"frame_count": frame_count, "atom_count": atom_count},
        events=("Current REPLAY-UNIFY1 immutable unified ExtXYZ source; sequential ASE parse baseline.",),
    )


WORKERS = {
    "target_data2b_reference_radii": _target_radii_worker,
    "target_data2b_feas1": _feas1_worker,
    "target_data2c_mvidx1": _mvidx1_worker,
    "target_data2c_mvsel1_kernel": _mvsel1_worker,
    "replay_unified_extxyz_ingest": _replay_worker,
}


def _spawn_workload(args: argparse.Namespace, workload: str, repeats: int) -> tuple[PerfBase1Trial, ...]:
    """Measure one workload in one controlled child process.

    Process startup/import cost is intentionally outside every trial meter.  A
    single child owns all repeated schedule trials so short CPU kernels are not
    distorted by repeated interpreter initialization and the parent never
    accumulates native cKDTree/threadpool teardown state across dozens of
    subprocesses.
    """
    command = [
        sys.executable, str(Path(__file__).resolve()), "--batch-worker", workload,
        "--repeats", str(max(2, int(repeats))),
        "--target-cache", str(args.target_cache), "--replay", str(args.replay),
    ]
    env = dict(os.environ)
    for key in (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    ):
        env[key] = "1"
    completed = subprocess.run(command, check=True, text=True, capture_output=True, env=env)
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    trials = tuple(PerfBase1Trial.from_dict(item) for item in payload["trials"])
    if payload.get("workload") != workload:
        raise RuntimeError(f"PERFBASE1 child workload mismatch: {payload.get('workload')!r} != {workload!r}")
    return trials

def _schedule() -> tuple[tuple[str, int], ...]:
    resources = detect_system_resources(device="cpu")
    budget = max(1, resources.cpu_threads_budget)
    dual = min(2, budget)
    intermediate = min(budget, max(2, budget // 2))
    return (("serial", 1), ("dual", dual), ("intermediate", intermediate), ("auto", budget))


def _artifact(path: Path, logical_path: str, role: str) -> PerfBase0ArtifactIdentity:
    return PerfBase0ArtifactIdentity.from_file(path, logical_path=logical_path, role=role)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--training-root", type=Path)
    p.add_argument("--target-cache", type=Path, required=True)
    p.add_argument("--training-archive", type=Path)
    p.add_argument("--replay", type=Path, required=True)
    p.add_argument("--foundation-model", type=Path)
    p.add_argument("--foundation-family", default="mace-mpa-0")
    p.add_argument("--foundation-variant", default="medium")
    p.add_argument("--source-package", type=Path)
    p.add_argument("--implementation-manifest", type=Path)
    p.add_argument("--dependencies-archive", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--report", type=Path)
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--baseline-id", default="lta-perfbase1-cloud-cpu-mpa0-2026-08-17")
    p.add_argument("--prepare-cache", action="store_true")
    p.add_argument("--worker", choices=tuple(WORKERS))
    p.add_argument("--batch-worker", choices=tuple(WORKERS))
    p.add_argument("--collect-workload", choices=tuple(WORKERS))
    p.add_argument("--bundle-output", type=Path)
    p.add_argument("--bundle-dir", type=Path)
    p.add_argument("--assemble-only", action="store_true")
    p.add_argument("--schedule-label", default="serial")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--repeat-index", type=int, default=0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.worker:
        trial = WORKERS[args.worker](args)
        print(json.dumps(trial.to_dict(), sort_keys=True))
        return 0
    if args.batch_worker:
        trials = []
        repeats = max(2, int(args.repeats))
        for label, workers in _schedule():
            for repeat_index in range(repeats):
                local = argparse.Namespace(**vars(args))
                local.schedule_label = label
                local.workers = workers
                local.repeat_index = repeat_index
                trials.append(WORKERS[args.batch_worker](local))
        print(json.dumps({"workload": args.batch_worker, "trials": [t.to_dict() for t in trials]}, sort_keys=True))
        return 0
    if args.collect_workload:
        if args.bundle_output is None:
            raise SystemExit("--bundle-output is required with --collect-workload.")
        trials = _spawn_workload(args, args.collect_workload, max(2, int(args.repeats)))
        args.bundle_output.parent.mkdir(parents=True, exist_ok=True)
        args.bundle_output.write_text(json.dumps({"workload": args.collect_workload, "trials": [t.to_dict() for t in trials]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"bundle": str(args.bundle_output), "trial_count": len(trials)}))
        return 0
    if args.prepare_cache or not args.target_cache.is_file():
        if args.training_root is None:
            raise SystemExit("--training-root is required to prepare the target family cache.")
        meta = _prepare_target_cache(args.training_root.resolve(), args.target_cache.resolve())
        print("PERFBASE1 target cache prepared:", json.dumps(meta, sort_keys=True))
    if args.foundation_model is None or not args.foundation_model.is_file():
        raise SystemExit("--foundation-model is required for PERFBASE1 model identity.")
    if args.output is None or args.report is None:
        raise SystemExit("--output and --report are required for the PERFBASE1 suite.")

    schedule = _schedule()
    repeats = max(2, int(args.repeats))
    workload_ids = tuple(WORKERS)
    trial_map: dict[str, list[PerfBase1Trial]] = {key: [] for key in workload_ids}
    for workload in workload_ids:
        bundle_path = None if args.bundle_dir is None else args.bundle_dir / f"{workload}.json"
        if bundle_path is not None and bundle_path.is_file():
            payload = json.loads(bundle_path.read_text(encoding="utf-8"))
            trial_map[workload].extend(PerfBase1Trial.from_dict(item) for item in payload["trials"])
            print(f"[PERFBASE1] loaded {workload} from {bundle_path}", flush=True)
        elif args.assemble_only:
            raise SystemExit(f"Missing PERFBASE1 trial bundle: {bundle_path}")
        else:
            print(f"[PERFBASE1] measuring {workload} across schedule={schedule} repeats={repeats}", flush=True)
            trial_map[workload].extend(_spawn_workload(args, workload, repeats))

    artifacts = tuple(
        _artifact(path, logical, role)
        for path, logical, role in (
            (args.training_archive, "inputs/training_LTA.tar.gz", "target_training_archive"),
            (args.replay, "inputs/replay_fps_12000.extxyz", "unified_replay_source"),
            (args.foundation_model, "inputs/foundation.model", "active_foundation_checkpoint"),
            (args.source_package, "inputs/mdstats_source_package.zip", "source_package"),
            (args.implementation_manifest, "inputs/perfbase1_implementation_manifest.json", "implementation_manifest"),
            (args.dependencies_archive, "inputs/dependencies.tar.gz", "dependency_bundle"),
            (args.target_cache, "inputs/perfbase1_target_family_cache.npz", "derived_target_family_cache"),
        ) if path is not None and Path(path).is_file()
    )
    artifact_by_role = {a.role: a for a in artifacts}
    target_corpus = digest({"archive": artifact_by_role.get("target_training_archive", artifact_by_role["derived_target_family_cache"]).sha256,
                            "cache": artifact_by_role["derived_target_family_cache"].sha256})
    replay_corpus = digest({"unified_replay": artifact_by_role["unified_replay_source"].sha256})
    synthetic_corpus = digest({"policy": SUITE_POLICY, "generator": "perfbase1-deterministic-synthetic-v1"})

    specs = {
        "target_data2b_reference_radii": ("supplied", (target_corpus,), "family-elements"),
        "target_data2b_feas1": ("synthetic", (synthetic_corpus,), "witnesses"),
        "target_data2c_mvidx1": ("synthetic", (synthetic_corpus,), "edges"),
        "target_data2c_mvsel1_kernel": ("synthetic", (synthetic_corpus,), "selected-ranks"),
        "replay_unified_extxyz_ingest": ("supplied", (replay_corpus,), "frames"),
    }
    workloads = []
    for workload_id in workload_ids:
        trials = tuple(trial_map[workload_id])
        outputs = {t.scientific_output_digest for t in trials}
        if len(outputs) != 1:
            raise SystemExit(f"PERFBASE1 scientific drift across trials for {workload_id}: {sorted(outputs)}")
        kind, corpora, unit = specs[workload_id]
        workloads.append(PerfBase1Workload(
            workload_id=workload_id,
            workload_kind=kind,
            corpus_digests=corpora,
            policy_digests=(SUITE_POLICY_DIGEST,),
            scientific_output_digest=trials[0].scientific_output_digest,
            throughput_unit=unit,
            trials=trials,
        ))

    model_sha = _sha256(args.foundation_model)
    unavailable = []
    try:
        import mace  # type: ignore  # noqa: F401
    except Exception:
        unavailable.extend((
            "FOUNDATION-AUDIT1 model-inference and residual-reduction baseline (MACE runtime unavailable on cloud host)",
            "EVAL2 checkpoint-inference/statistics baseline (MACE runtime unavailable on cloud host)",
        ))
    record = PerfBase1Record(
        baseline_id=args.baseline_id,
        source_version=mdstats.__version__,
        created_at_utc=workloads[0].trials[0].measured_at_utc,
        foundation_family=args.foundation_family,
        foundation_variant=args.foundation_variant,
        foundation_model_sha256=model_sha,
        source_artifacts=artifacts,
        workloads=tuple(workloads),
        unavailable_workloads=tuple(unavailable),
        limitations=(
            "Cloud CPU authority is cgroup-constrained; automatic workers use mdstats' detected CPU budget.",
            "TARGET-DATA2B family extraction/target XML parsing is performed once outside timed radius trials; replay parsing is timed directly.",
            "FEAS1/MVIDX1/MVSEL1 scaling workloads are deterministic synthetic authorities so algorithmic changes can be compared without model inference noise.",
            "No GPU performance authority is asserted by PERFBASE1.",
        ),
    )
    write_perfbase1_record(args.output, record)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_perfbase1_markdown(record), encoding="utf-8")
    restored = mdstats.read_perfbase1_record(args.output)
    if restored.content_digest != record.content_digest:
        raise SystemExit("PERFBASE1 round-trip digest mismatch.")
    print(json.dumps({
        "output": str(args.output), "report": str(args.report),
        "scientific_digest": record.scientific_digest,
        "execution_digest": record.execution_digest,
        "content_digest": record.content_digest,
        "schedule": schedule,
        "foundation_model_sha256": model_sha,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
