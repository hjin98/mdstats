#!/usr/bin/env python3
"""Bounded CPU/control-plane benchmark for VRAM1 + PERF-P4.

This benchmark intentionally makes no accelerator-performance or VRAM claim.
It verifies that synchronous and bounded-pipeline DATA6 execution produce the
same scientific artifacts on the deterministic production-sweep fixture, and
measures the CPU-side orchestration cost.  CUDA/VRAM throughput qualification
is deferred to FINAL-GPU1.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import mdstats
from tests.test_mlff_data9a9a_production_model_sweep import _CountingCalculator, _inputs, _provider

SCHEMA = "mdstats.vram1-perf-p4-cpu-benchmark.2026-08.v1"


def _proc_io() -> dict[str, int]:
    result: dict[str, int] = {}
    try:
        for line in Path("/proc/self/io").read_text().splitlines():
            key, value = line.split(":", 1)
            result[key.strip()] = int(value.strip())
    except (FileNotFoundError, OSError, ValueError):
        pass
    return result


def _run_once(*, root: Path, frames, frame_data, data5, policy, pipeline: bool) -> dict[str, Any]:
    io0 = _proc_io()
    cpu0 = time.process_time()
    wall0 = time.perf_counter()
    artifacts = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        _provider(_CountingCalculator()),
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            batch_size=4,
            artifact_shard_size=3,
            pipeline_enabled=pipeline,
            persistence_queue_depth=1,
        ),
    )
    wall = time.perf_counter() - wall0
    cpu = time.process_time() - cpu0
    io1 = _proc_io()
    if not artifacts.complete:
        raise RuntimeError("DATA6 benchmark sweep did not complete")
    return {
        "wall_seconds": wall,
        "process_cpu_seconds": cpu,
        "io_delta": {key: io1.get(key, 0) - io0.get(key, 0) for key in sorted(set(io0) | set(io1))},
        "artifacts": artifacts,
    }


def _scientific_signature(artifacts, root: Path) -> dict[str, Any]:
    descriptor = []
    if artifacts.descriptor_manifest is not None:
        for uid in artifacts.checkpoint.plan.descriptor_frame_uids:
            value = mdstats.read_mace_descriptor_array(artifacts.descriptor_manifest, root, uid)
            descriptor.append((uid, value.dtype.str, list(value.shape), value.tobytes().hex()))
    predictions = []
    if artifacts.prediction_manifest is not None:
        for uid in artifacts.checkpoint.plan.prediction_frame_uids:
            value = mdstats.read_atomic_model_prediction(artifacts.prediction_manifest, root, uid)
            predictions.append(
                (
                    uid,
                    float(value.energy_ev),
                    value.forces_ev_per_angstrom.dtype.str,
                    list(value.forces_ev_per_angstrom.shape),
                    value.forces_ev_per_angstrom.tobytes().hex(),
                    None if value.stress_ev_per_angstrom3 is None else value.stress_ev_per_angstrom3.tobytes().hex(),
                )
            )
    payload = {
        "plan_digest": artifacts.checkpoint.plan.content_digest,
        "frame_uids": [record.frame_uid for record in artifacts.checkpoint.records],
        "descriptors": descriptor,
        "predictions": predictions,
    }
    from mdstats.training_data._common import digest
    return {"content_digest": digest(payload), "payload": payload}


def _summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    wall = [float(item["wall_seconds"]) for item in samples]
    cpu = [float(item["process_cpu_seconds"]) for item in samples]
    return {
        "count": len(samples),
        "wall_seconds": {"minimum": min(wall), "median": statistics.median(wall), "maximum": max(wall)},
        "process_cpu_seconds": {"minimum": min(cpu), "median": statistics.median(cpu), "maximum": max(cpu)},
        "write_characters_median": statistics.median([int(item["io_delta"].get("wchar", 0)) for item in samples]),
        "read_characters_median": statistics.median([int(item["io_delta"].get("rchar", 0)) for item in samples]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=15)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error("--repeats must be at least 3")

    with tempfile.TemporaryDirectory(prefix="mdstats-vram1-p4-") as td:
        base = Path(td)
        _, frames, frame_data, _, data5, policy = _inputs(base)
        modes = (False, True)
        samples: dict[bool, list[dict[str, Any]]] = {False: [], True: []}
        signatures: dict[bool, list[str]] = {False: [], True: []}
        reference_signature: str | None = None
        # Alternate ordering to reduce monotone host-state bias.
        for repeat in range(args.repeats):
            for pipeline in (modes if repeat % 2 == 0 else tuple(reversed(modes))):
                root = base / f"run-{repeat:02d}-{'pipeline' if pipeline else 'sync'}"
                shutil.rmtree(root, ignore_errors=True)
                sample = _run_once(
                    root=root,
                    frames=frames,
                    frame_data=frame_data,
                    data5=data5,
                    policy=policy,
                    pipeline=pipeline,
                )
                artifacts = sample.pop("artifacts")
                signature = _scientific_signature(artifacts, root)["content_digest"]
                if reference_signature is None:
                    reference_signature = signature
                signatures[pipeline].append(signature)
                samples[pipeline].append(sample)

        sync = _summary(samples[False])
        pipeline = _summary(samples[True])
        exact = all(value == reference_signature for values in signatures.values() for value in values)
        sync_median = float(sync["wall_seconds"]["median"])
        pipe_median = float(pipeline["wall_seconds"]["median"])
        result = {
            "schema": SCHEMA,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "mdstats_version": mdstats.__version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_model": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.lower().startswith("model name")
                ),
                "unknown",
            ),
            "logical_cpu_count": os.cpu_count(),
            "scope": "cpu_control_plane_only_gpu_and_vram_qualification_deferred_to_FINAL_GPU1",
            "fixture": {
                "frame_catalog_digest": frames.content_digest,
                "data5_bundle_digest": data5.content_digest,
                "requested_frames": len(mdstats.build_data6_model_sweep_plan(frames, data5, policy, _provider(_CountingCalculator()).checkpoint_identity).requested_frame_uids),
                "batch_size": 4,
                "artifact_shard_size": 3,
                "persistence_queue_depth": 1,
            },
            "scientific_authority_exact": exact,
            "scientific_signature": reference_signature,
            "synchronous": sync,
            "bounded_pipeline": pipeline,
            "pipeline_wall_change_fraction": (pipe_median / sync_median - 1.0) if sync_median else None,
            "interpretation": (
                "CPU fixture measures orchestration overhead only; a positive wall-change fraction is not a PERF-P4 failure. "
                "The synchronous path is the exact fallback and accelerator throughput/VRAM admission remains a FINAL-GPU1 obligation."
            ),
        }

    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
