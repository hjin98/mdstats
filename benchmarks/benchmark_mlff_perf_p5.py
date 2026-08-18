#!/usr/bin/env python3
"""PERF-P5 CPU benchmark for streamed tensor hashing and EVAL2 shell reuse."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import time
from typing import Any


def _legacy_train2_digest(tensors: list[Any], *, schema: str) -> str:
    h = hashlib.sha256(); h.update(schema.encode("utf-8"))
    for item in tensors:
        value = item.detach().cpu().contiguous()
        h.update(str(value.dtype).encode("utf-8"))
        h.update(repr(tuple(value.shape)).encode("utf-8"))
        h.update(bytes(value.numpy().tobytes()))
    return h.hexdigest()


def _legacy_capsule_digest(state: dict[str, Any], torch: Any) -> str:
    h = hashlib.sha256()
    for key in sorted(state):
        tensor = state[key].detach().cpu().contiguous()
        h.update(key.encode("utf-8")); h.update(b"\0")
        h.update(str(tensor.dtype).encode("ascii")); h.update(b"\0")
        h.update(json.dumps(tuple(int(v) for v in tensor.shape)).encode("ascii")); h.update(b"\0")
        try:
            payload = tensor.numpy().tobytes(order="C")
        except Exception:
            payload = tensor.view(torch.uint8).numpy().tobytes(order="C")
        h.update(payload); h.update(b"\xff")
    return h.hexdigest()


def _worker(mode: str, elements: int) -> None:
    import torch
    from mdstats.training_data import checkpoint_capsule, train2_runtime

    tensor = torch.zeros(elements, dtype=torch.float32)
    state = {"model.weight": tensor}
    gc.collect()
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    started = time.perf_counter()
    if mode == "legacy_train2":
        value = _legacy_train2_digest([tensor], schema="mdstats.train2-live-parameters.v1")
    elif mode == "stream_train2":
        value = train2_runtime._tensor_state_digest([tensor], schema="mdstats.train2-live-parameters.v1")
    elif mode == "legacy_capsule":
        value = _legacy_capsule_digest(state, torch)
    elif mode == "stream_capsule":
        value = checkpoint_capsule.model_state_sha256(state)
    else:  # pragma: no cover
        raise ValueError(mode)
    elapsed = time.perf_counter() - started
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({
        "mode": mode,
        "elapsed_seconds": elapsed,
        "digest": value,
        "peak_rss_increment_mib": max(0, rss_after - rss_before) / 1024.0,
        "tensor_bytes": tensor.numel() * tensor.element_size(),
    }, sort_keys=True))


def _run_worker(mode: str, elements: int) -> dict[str, Any]:
    env = dict(os.environ)
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    result = subprocess.run(
        [sys.executable, __file__, "--worker", mode, "--elements", str(elements)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "repetitions": len(records),
        "median_wall_seconds": statistics.median(r["elapsed_seconds"] for r in records),
        "wall_seconds": [r["elapsed_seconds"] for r in records],
        "median_peak_rss_increment_mib": statistics.median(r["peak_rss_increment_mib"] for r in records),
        "peak_rss_increment_mib": [r["peak_rss_increment_mib"] for r in records],
        "digest": records[0]["digest"],
        "digest_invariant": len({r["digest"] for r in records}) == 1,
    }


def _shell_benchmark(model: Path, repetitions: int, head: str) -> dict[str, Any]:
    from mdstats.training_data.model_features import MaceCalculatorProvider

    kwargs = {"device": "cpu", "default_dtype": "float64", "head": head}
    shell = MaceCalculatorProvider.from_model_path(model, **kwargs)
    fresh: list[float] = []
    hot: list[float] = []
    for _ in range(repetitions):
        gc.collect(); started = time.perf_counter()
        provider = MaceCalculatorProvider.from_model_path(model, **kwargs)
        fresh.append(time.perf_counter() - started); del provider
        gc.collect(); started = time.perf_counter()
        shell.load_compatible_model_state(model)
        hot.append(time.perf_counter() - started)
    return {
        "model": str(model),
        "head": head,
        "fresh_median_wall_seconds": statistics.median(fresh),
        "hot_swap_median_wall_seconds": statistics.median(hot),
        "fresh_wall_seconds": fresh,
        "hot_swap_wall_seconds": hot,
        "hot_swap_faster_on_cpu": statistics.median(hot) < statistics.median(fresh),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("legacy_train2", "stream_train2", "legacy_capsule", "stream_capsule"))
    parser.add_argument("--elements", type=int, default=64_000_000)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--head", default="omat_pbe")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker:
        _worker(args.worker, args.elements)
        return

    modes = ("legacy_train2", "stream_train2", "legacy_capsule", "stream_capsule")
    records = {mode: [_run_worker(mode, args.elements) for _ in range(args.repetitions)] for mode in modes}
    result: dict[str, Any] = {
        "schema": "mdstats.perf-p5-cpu-benchmark.v1",
        "tensor_elements": args.elements,
        "tensor_bytes": args.elements * 4,
        "hashing": {mode: _summary(values) for mode, values in records.items()},
    }
    result["train2_digest_equal"] = result["hashing"]["legacy_train2"]["digest"] == result["hashing"]["stream_train2"]["digest"]
    result["capsule_digest_equal"] = result["hashing"]["legacy_capsule"]["digest"] == result["hashing"]["stream_capsule"]["digest"]
    if args.model is not None:
        result["eval2_shell"] = _shell_benchmark(args.model.resolve(), max(3, args.repetitions), args.head)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
