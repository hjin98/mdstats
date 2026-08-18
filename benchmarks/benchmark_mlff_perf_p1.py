#!/usr/bin/env python3
"""Qualify PERF-P1 exact selection and progressive coverage against PERF-P0."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
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
from mdstats.training_data._common import canonical_json, digest
from mdstats.training_data.selection import (
    _extend_selected_neighbor_matrix,
    _extend_selected_neighbor_minima,
    _fps_order_matrix,
    _update_min_squared_distances,
)
from mdstats.training_data.target_coverage import (
    score_target_nested_subsets_coverage,
    score_target_subset_coverage,
)
from mdstats.training_data.target_ladder import _fused_required_family_matrix, _weighted_median

SCHEMA = "mdstats.mlff-perf-p1-benchmark.v1"


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

    def measurement(self, wall: float, cpu: float) -> Measurement:
        scale = 1024.0 * 1024.0
        return Measurement(
            wall_seconds=wall,
            process_cpu_seconds=cpu,
            rss_start_mib=self.start / scale,
            rss_end_mib=self.end / scale,
            rss_peak_mib=self.peak / scale,
            rss_increment_mib=max(0, self.peak - self.start) / scale,
        )


def _measure(fn: Callable[[], Any]) -> tuple[Any, Measurement]:
    with _RssMonitor() as monitor:
        w0 = time.perf_counter(); c0 = time.process_time()
        value = fn()
        cpu = time.process_time() - c0; wall = time.perf_counter() - w0
    return value, monitor.measurement(wall, cpu)


def _legacy_fused_required_family_matrix(domain: Any) -> np.ndarray:
    required = tuple(sorted((item for item in domain.families if item.required), key=lambda item: item.family_id))
    by_semantic: dict[str, list[Any]] = {}
    for family in required:
        by_semantic.setdefault(family.semantic_family, []).append(family)
    semantic_ids = tuple(sorted(by_semantic))
    n_frames = len(domain.frame_uids)
    blocks: list[np.ndarray] = []
    for semantic in semantic_ids:
        families = tuple(sorted(by_semantic[semantic], key=lambda item: item.family_id))
        family_factor = 1.0 / math.sqrt(float(len(families)))
        for family in families:
            values = np.asarray(family.values, dtype=np.float64)
            weights = np.asarray(family.weights, dtype=np.float64)
            scales = np.asarray(family.scales, dtype=np.float64)
            scaled = values / scales[None, :]
            center = _weighted_median(scaled, weights)
            d = scaled.shape[1]
            block = np.zeros((n_frames, d + 1), dtype=np.float64)
            rows = np.asarray(family.frame_indices, dtype=np.int64)
            block[rows, :d] = scaled - center[None, :]
            if len(rows) < n_frames:
                block[:, d] = -0.5
                block[rows, d] = 0.5
            block *= family_factor / math.sqrt(float(d + 1))
            blocks.append(block)
    matrix = np.concatenate(blocks, axis=1)
    matrix /= math.sqrt(float(len(semantic_ids)))
    return matrix


def _legacy_fps_order_matrix(
    frame_uids: Sequence[str], matrix: np.ndarray, initial: Sequence[str], tolerance: float, *, limit: int
) -> list[str]:
    uids = tuple(str(uid) for uid in frame_uids)
    X = np.asarray(matrix, dtype=np.float64)
    target = min(max(0, int(limit)), len(uids))
    uid_to_index = {uid: index for index, uid in enumerate(uids)}
    selected_mask = np.zeros(len(uids), dtype=np.bool_)
    initial_indices = [uid_to_index[uid] for uid in dict.fromkeys(initial) if uid in uid_to_index]
    if initial_indices:
        selected_mask[np.asarray(initial_indices, dtype=np.int64)] = True
    min_squared = np.full(len(uids), np.inf, dtype=np.float64)
    if initial_indices:
        _update_min_squared_distances(X, X[np.asarray(initial_indices, dtype=np.int64)], min_squared)
    result: list[str] = []
    if not initial_indices and np.any(~selected_mask):
        centroid = np.mean(X, axis=0)
        squared = np.einsum("ij,ij->i", X - centroid, X - centroid)
        best_score = float(np.sqrt(np.max(squared)))
        candidates = np.flatnonzero(np.abs(np.sqrt(squared) - best_score) <= tolerance)
        first = min((int(index) for index in candidates), key=lambda index: uids[index])
        selected_mask[first] = True; result.append(uids[first])
        _update_min_squared_distances(X, X[first], min_squared)
    while len(result) < target and np.any(~selected_mask):
        available = np.flatnonzero(~selected_mask)
        scores = np.sqrt(min_squared[available]); best_score = float(np.max(scores))
        tied = available[np.abs(scores - best_score) <= tolerance]
        best = min((int(index) for index in tied), key=lambda index: uids[index])
        selected_mask[best] = True; result.append(uids[best])
        _update_min_squared_distances(X, X[best], min_squared)
    return result


def _summary(items: Sequence[Measurement]) -> dict[str, Any]:
    def stats(name: str) -> dict[str, float]:
        values = np.asarray([getattr(item, name) for item in items], dtype=np.float64)
        return {"min": float(np.min(values)), "median": float(np.median(values)), "max": float(np.max(values))}
    return {name: stats(name) for name in ("wall_seconds", "process_cpu_seconds", "rss_peak_mib", "rss_increment_mib")}


def _array_sha256(array: np.ndarray) -> str:
    x = np.ascontiguousarray(np.asarray(array, dtype="<f8"))
    return hashlib.sha256(memoryview(x).cast("B")).hexdigest()


def _neighbor_child(mode: str, k: int, dimension: int, budget: int) -> None:
    rng = np.random.default_rng(2026081507)
    X = rng.normal(size=(k, dimension)).astype(np.float64)
    rungs = tuple(v for v in (1024, 2048, 4096, 8192) if v <= k)
    if not rungs or rungs[-1] != k:
        rungs = (*rungs, k)
    w0 = time.perf_counter(); c0 = time.process_time(); previous = 0
    if mode == "legacy":
        squared = np.full((k, k), np.inf, dtype=np.float64)
        for current in rungs:
            _extend_selected_neighbor_matrix(X, squared, previous, current)
            previous = current
        minima = np.min(squared, axis=1)
        persistent_bytes = squared.nbytes
    else:
        minima = np.full(k, np.inf, dtype=np.float64)
        for current in rungs:
            _extend_selected_neighbor_minima(X, minima, previous, current, memory_budget_bytes=budget)
            previous = current
        persistent_bytes = minima.nbytes
    payload = {
        "mode": mode,
        "k": k,
        "dimension": dimension,
        "rungs": list(rungs),
        "wall_seconds": time.perf_counter() - w0,
        "process_cpu_seconds": time.process_time() - c0,
        "rss_peak_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        "persistent_bytes": int(persistent_bytes),
        "minima_sha256": _array_sha256(minima),
    }
    print(json.dumps(payload, sort_keys=True))


def _run_neighbor_subprocess(mode: str, *, k: int, dimension: int, budget: int) -> dict[str, Any]:
    command = [sys.executable, __file__, "--neighbor-child", mode, "--neighbor-k", str(k), "--neighbor-dimension", str(dimension), "--neighbor-budget", str(budget)]
    result = subprocess.run(command, check=True, capture_output=True, text=True, env=os.environ.copy())
    return json.loads(result.stdout.strip().splitlines()[-1])


def _host() -> dict[str, Any]:
    cpu = "unknown"
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                cpu = line.split(':',1)[1].strip(); break
    except OSError: pass
    quota = None
    try: quota = Path('/sys/fs/cgroup/cpu.max').read_text().strip()
    except OSError: pass
    memory = None
    try: memory = Path('/sys/fs/cgroup/memory.max').read_text().strip()
    except OSError: pass
    return {"platform": platform.platform(), "python": platform.python_version(), "cpu_model": cpu, "logical_cpus": os.cpu_count(), "cgroup_cpu_max": quota, "cgroup_memory_max": memory, "openblas_num_threads": os.environ.get('OPENBLAS_NUM_THREADS'), "omp_num_threads": os.environ.get('OMP_NUM_THREADS')}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--p0-evidence', type=Path, default=Path('/mnt/data/mdstats_release_179/mlff_perf_p0_lta_cloud_cpu_2026-08-15.json'))
    parser.add_argument('--reference-root', type=Path, default=Path('/mnt/data/mdstats_perf_p0/persistence_stages'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--fps-limit', type=int, default=1024)
    parser.add_argument('--neighbor-child', choices=('legacy','p1'))
    parser.add_argument('--neighbor-k', type=int, default=8192)
    parser.add_argument('--neighbor-dimension', type=int, default=16)
    parser.add_argument('--neighbor-budget', type=int, default=256*1024*1024)
    args = parser.parse_args()
    if args.neighbor_child:
        _neighbor_child(args.neighbor_child, args.neighbor_k, args.neighbor_dimension, args.neighbor_budget); return

    p0 = json.loads(args.p0_evidence.read_text())
    pointer = p0['persistence']['native_v2']['pointer']
    reference = mdstats.read_target_coverage_native_record(pointer, args.reference_root, mmap_threshold_bytes=0)
    domain = reference.domains[0]
    repeats = max(1, int(args.repeats))

    legacy_assembly_m: list[Measurement] = []; p1_assembly_m: list[Measurement] = []
    legacy_matrix = p1_matrix = None
    for _ in range(repeats):
        legacy_matrix, m = _measure(lambda: _legacy_fused_required_family_matrix(domain)); legacy_assembly_m.append(m)
        built, m = _measure(lambda: _fused_required_family_matrix(domain)); p1_assembly_m.append(m); p1_matrix = built[0]
    assert legacy_matrix is not None and p1_matrix is not None
    matrix_exact = bool(np.array_equal(legacy_matrix, p1_matrix))

    legacy_fps_m: list[Measurement] = []; p1_fps_m: list[Measurement] = []
    legacy_order = p1_order = None
    for _ in range(repeats):
        legacy_order, m = _measure(lambda: _legacy_fps_order_matrix(domain.frame_uids, p1_matrix, (), 1e-12, limit=args.fps_limit)); legacy_fps_m.append(m)
        p1_order, m = _measure(lambda: _fps_order_matrix(domain.frame_uids, p1_matrix, (), 1e-12, limit=args.fps_limit)); p1_fps_m.append(m)
    assert legacy_order is not None and p1_order is not None
    fps_exact = legacy_order == p1_order
    rung_sizes = tuple(v for v in (128,256,512,1024,2048,4096,8192) if v <= len(p1_order))
    if not rung_sizes or rung_sizes[-1] != len(p1_order): rung_sizes = (*rung_sizes, len(p1_order))
    subsets = tuple(p1_order[:k] for k in rung_sizes)

    legacy_cov_m: list[Measurement] = []; p1_cov_m: list[Measurement] = []
    legacy_reports = p1_reports = None
    for _ in range(repeats):
        legacy_reports, m = _measure(lambda: tuple(score_target_subset_coverage(reference, domain.label_domain_id, subset) for subset in subsets)); legacy_cov_m.append(m)
        p1_reports, m = _measure(lambda: score_target_nested_subsets_coverage(reference, domain.label_domain_id, subsets, query_workers=1)); p1_cov_m.append(m)
    assert legacy_reports is not None and p1_reports is not None
    coverage_exact = [r.content_digest for r in legacy_reports] == [r.content_digest for r in p1_reports]

    # Wide deterministic synthetic FPS qualification.
    rng = np.random.default_rng(2026081509)
    wide = rng.normal(size=(4000,128)).astype(np.float64)
    wide_uids = tuple(f"{i:064x}" for i in range(len(wide)))
    wide_limit = 512
    legacy_wide, legacy_wide_m = _measure(lambda: _legacy_fps_order_matrix(wide_uids,wide,(),1e-12,limit=wide_limit))
    p1_wide, p1_wide_m = _measure(lambda: _fps_order_matrix(wide_uids,wide,(),1e-12,limit=wide_limit))

    legacy_neighbor = _run_neighbor_subprocess('legacy', k=args.neighbor_k, dimension=args.neighbor_dimension, budget=args.neighbor_budget)
    p1_neighbor = _run_neighbor_subprocess('p1', k=args.neighbor_k, dimension=args.neighbor_dimension, budget=args.neighbor_budget)

    scientific = {
        "reference_content_digest": reference.content_digest,
        "matrix_exact": matrix_exact,
        "fps_order_exact": fps_exact,
        "coverage_report_exact": coverage_exact,
        "fps_order_digest": digest({"order": p1_order}),
        "coverage_report_digests": [r.content_digest for r in p1_reports],
        "wide_fps_exact": legacy_wide == p1_wide,
        "wide_fps_order_digest": digest({"order": p1_wide}),
        "selected_neighbor_exact": legacy_neighbor['minima_sha256'] == p1_neighbor['minima_sha256'],
        "selected_neighbor_minima_sha256": p1_neighbor['minima_sha256'],
    }
    execution = {
        "host": _host(),
        "repeats": repeats,
        "target_frames": len(domain.frame_uids),
        "target_matrix_shape": list(p1_matrix.shape),
        "fps_limit": args.fps_limit,
        "rung_sizes": list(rung_sizes),
        "assembly": {"legacy": [asdict(x) for x in legacy_assembly_m], "p1": [asdict(x) for x in p1_assembly_m], "legacy_summary": _summary(legacy_assembly_m), "p1_summary": _summary(p1_assembly_m)},
        "fps": {"legacy": [asdict(x) for x in legacy_fps_m], "p1": [asdict(x) for x in p1_fps_m], "legacy_summary": _summary(legacy_fps_m), "p1_summary": _summary(p1_fps_m)},
        "coverage": {"legacy": [asdict(x) for x in legacy_cov_m], "p1": [asdict(x) for x in p1_cov_m], "legacy_summary": _summary(legacy_cov_m), "p1_summary": _summary(p1_cov_m)},
        "wide_fps": {"shape": list(wide.shape), "limit": wide_limit, "legacy": asdict(legacy_wide_m), "p1": asdict(p1_wide_m)},
        "selected_neighbor": {"legacy": legacy_neighbor, "p1": p1_neighbor, "memory_budget_bytes": args.neighbor_budget},
    }
    payload = {"schema": SCHEMA, "source_version": mdstats.__version__, "scientific": scientific, "execution": execution}
    payload['scientific_digest'] = digest(scientific); payload['execution_digest'] = digest(execution)
    payload['content_digest'] = digest({"schema":SCHEMA,"source_version":mdstats.__version__,"scientific_digest":payload['scientific_digest'],"execution_digest":payload['execution_digest']})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(canonical_json(payload)+'\n')
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
