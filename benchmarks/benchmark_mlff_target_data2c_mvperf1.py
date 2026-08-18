#!/usr/bin/env python3
"""TARGET-DATA2C-MVPERF1 exact selector execution benchmark.

The benchmark uses deterministic sparse ring graphs so it measures selector
execution rather than descriptor/KD-tree construction.  The reference and
optimized workers consume identical graphs and must produce the same ordered
selection digest.  A larger cardinality worker exercises the 16,384 selection
ceiling without requiring the expensive reference implementation at that scale.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from typing import Any

import numpy as np


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
        self._families = {
            family.family_id: _ReferenceFamily(family.family_id, n, i / 11.0)
            for i, family in enumerate(families)
        }

    def family(self, family_id: str) -> _ReferenceFamily:
        return self._families[family_id]


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

    def candidate_obligation_indices(self, candidate: int) -> np.ndarray:
        return np.empty(0, dtype=np.uint32)

    def obligation_candidate_indices(self, obligation: int) -> np.ndarray:
        return np.empty(0, dtype=np.uint32)


def _run(mode: str, n: int, k: int, degree: int, family_count: int) -> dict[str, Any]:
    from mdstats.training_data import target_multi_view_selector as mvsel

    families = tuple(_SparseFamily(f"family_{i}", n, degree, 2 * i + 1) for i in range(family_count))
    reference = _ReferenceDomain(n, families)
    sparse = _SparseDomain(n, families)
    policy = mvsel.TargetMultiViewSelectorPolicy(target_sizes=(k,))
    update = mvsel._select_and_update if mode == "optimized" else mvsel._select_and_update_reference
    state = mvsel._build_domain_state(reference, sparse)
    selected: list[int] = []
    started = time.perf_counter()
    cpu_started = time.process_time()
    for _ in range(k):
        candidate, _, _, _ = mvsel._choose_candidate(reference, sparse, state, policy)
        selected.append(candidate)
        update(candidate, sparse, state)
    wall = time.perf_counter() - started
    cpu = time.process_time() - cpu_started
    h = hashlib.sha256(np.asarray(selected, dtype="<u4").tobytes()).hexdigest()
    return {
        "mode": mode,
        "n": n,
        "k": k,
        "degree": degree,
        "family_count": family_count,
        "edge_count": n * degree * family_count,
        "wall_seconds": wall,
        "cpu_seconds": cpu,
        "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "selection_digest": h,
    }


def _worker(args: argparse.Namespace) -> None:
    if args.worker == "reference":
        result = _run("reference", args.reference_n, args.reference_k, args.reference_degree, args.reference_families)
    elif args.worker == "optimized":
        result = _run("optimized", args.reference_n, args.reference_k, args.reference_degree, args.reference_families)
    else:
        result = _run("optimized", args.scale_n, args.scale_k, args.scale_degree, args.scale_families)
    print(json.dumps(result, sort_keys=True))


def _spawn(mode: str, args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable, __file__, "--worker", mode,
        "--reference-n", str(args.reference_n), "--reference-k", str(args.reference_k),
        "--reference-degree", str(args.reference_degree), "--reference-families", str(args.reference_families),
        "--scale-n", str(args.scale_n), "--scale-k", str(args.scale_k),
        "--scale-degree", str(args.scale_degree), "--scale-families", str(args.scale_families),
    ]
    env = dict(os.environ)
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    completed = subprocess.run(command, check=True, text=True, capture_output=True, env=env)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("reference", "optimized", "scale"))
    parser.add_argument("--reference-n", type=int, default=4096)
    parser.add_argument("--reference-k", type=int, default=2048)
    parser.add_argument("--reference-degree", type=int, default=24)
    parser.add_argument("--reference-families", type=int, default=3)
    parser.add_argument("--scale-n", type=int, default=24576)
    parser.add_argument("--scale-k", type=int, default=16384)
    parser.add_argument("--scale-degree", type=int, default=8)
    parser.add_argument("--scale-families", type=int, default=2)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.worker:
        _worker(args)
        return
    reference = _spawn("reference", args)
    optimized = _spawn("optimized", args)
    scale = _spawn("scale", args)
    result = {
        "schema": "mdstats.target-data2c-mvperf1-benchmark.v1",
        "release": __import__("mdstats").__version__,
        "reference": reference,
        "optimized": optimized,
        "scale": scale,
        "decision_equivalent": reference["selection_digest"] == optimized["selection_digest"],
        "selector_speedup": reference["wall_seconds"] / optimized["wall_seconds"],
        "optimized_rss_ratio": optimized["maxrss_kib"] / max(1, reference["maxrss_kib"]),
        "scale_completed_16384": scale["k"] == 16384,
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
