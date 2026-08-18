#!/usr/bin/env python3
"""MVKERNEL1 exact sparse selector/qualification kernel benchmark."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import statistics
import time
from types import SimpleNamespace
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
    label_domain_id = "mvkernel1"
    content_digest = "a" * 64
    frame_domain_digest = "b" * 64

    def __init__(self, n: int, families: tuple[_SparseFamily, ...]) -> None:
        self.frame_uids = tuple(hashlib.sha256(f"mvkernel1-frame-{i:08d}".encode()).hexdigest() for i in range(n))
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


def _fixture(n: int, degree: int, family_count: int):
    families = tuple(_SparseFamily(f"family_{i}", n, degree, 2 * i + 1) for i in range(family_count))
    return _ReferenceDomain(n, families), _SparseDomain(n, families)


def _selector_once(n: int, k: int, degree: int, family_count: int) -> dict[str, Any]:
    from mdstats.training_data import target_multi_view_selector as mvsel

    reference, sparse = _fixture(n, degree, family_count)
    policy = mvsel.TargetMultiViewSelectorPolicy(target_sizes=(k,))
    state = mvsel._build_domain_state(reference, sparse)
    selected: list[int] = []
    started = time.perf_counter(); cpu_started = time.process_time()
    for _ in range(k):
        candidate, _, _, _ = mvsel._choose_candidate(reference, sparse, state, policy)
        selected.append(candidate)
        mvsel._select_and_update(candidate, sparse, state)
    wall = time.perf_counter() - started; cpu = time.process_time() - cpu_started
    return {
        "wall_seconds": wall,
        "cpu_seconds": cpu,
        "selection_digest": hashlib.sha256(np.asarray(selected, dtype="<u4").tobytes()).hexdigest(),
        "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def _selector_benchmark(repeats: int) -> dict[str, Any]:
    trials = [_selector_once(4096, 2048, 24, 3) for _ in range(repeats)]
    scale = _selector_once(24576, 16384, 8, 2)
    return {
        "fixture": {"n": 4096, "k": 2048, "degree": 24, "family_count": 3, "edge_count": 294912},
        "trial_wall_seconds": [x["wall_seconds"] for x in trials],
        "median_wall_seconds": statistics.median(x["wall_seconds"] for x in trials),
        "selection_digests": sorted({x["selection_digest"] for x in trials}),
        "scale": {
            "n": 24576, "k": 16384, "degree": 8, "family_count": 2, "edge_count": 393216,
            **scale,
        },
    }


def _telemetry_benchmark(repeats: int) -> dict[str, Any]:
    from mdstats.training_data import target_multi_view_qualification as mvqual

    n, k, degree, family_count = 16384, 8192, 16, 6
    reference, sparse = _fixture(n, degree, family_count)
    role = SimpleNamespace(development_intervals=(SimpleNamespace(
        frame_uids=reference.frame_uids, run_id="run0", condition_id="condition0", unit_id="unit0"
    ),))
    selected_uids = reference.frame_uids[:k]
    # Warm once so the timed region represents the kernel, not first-call import/cache effects.
    authority = mvqual._selector_telemetry(reference, sparse, role, selected_uids).to_dict()
    trials = []
    for _ in range(repeats):
        started = time.perf_counter(); cpu_started = time.process_time()
        result = mvqual._selector_telemetry(reference, sparse, role, selected_uids).to_dict()
        trials.append((time.perf_counter() - started, time.process_time() - cpu_started))
        if result != authority:
            raise RuntimeError("MVKERNEL1 telemetry benchmark changed authority across repeats.")
    authority_digest = hashlib.sha256(
        json.dumps(authority, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "fixture": {"n": n, "k": k, "degree": degree, "family_count": family_count, "edge_count": n * degree * family_count},
        "trial_wall_seconds": [x[0] for x in trials],
        "median_wall_seconds": statistics.median(x[0] for x in trials),
        "authority_digest": authority_digest,
        "authority": authority,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("selector", "telemetry", "all"), default="all")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output")
    args = parser.parse_args()
    result: dict[str, Any] = {
        "schema": "mdstats.mlff-mvkernel1-benchmark.v1",
        "release": __import__("mdstats").__version__,
    }
    if args.mode in {"selector", "all"}:
        result["selector"] = _selector_benchmark(args.repeats)
    if args.mode in {"telemetry", "all"}:
        result["telemetry"] = _telemetry_benchmark(args.repeats)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
