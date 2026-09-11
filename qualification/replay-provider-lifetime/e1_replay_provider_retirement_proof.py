"""E1 - real MACE/CUDA in-process provider-retirement proof.

Drives the *production* replay prediction owner
(`build_replay_foundation_prediction_cache` with ``provider=None``, so the owner
constructs the provider, transfers it once, and must retire it itself) on the
real MH-1 checkpoint and the real replay corpus, in a process that stays alive
afterwards.  NVML aggregate/process occupancy and PyTorch
allocated/reserved/max are captured around acquisition, inference peak, final
consumer, close, and post-close.

Two independent cold builds are run.  One cycle can only show that occupancy
fell; two cycles show that whatever residency remains after an explicit close is
*bounded and non-accumulating* - the difference between a retired owner and a
leaked one.
"""
from __future__ import annotations

import gc
import json
import os
import shutil
import sys
from pathlib import Path

import torch

import mdstats
from mdstats.training_data.foundation import MaceFoundationSpec
from mdstats.training_data import replay_pseudolabel as rp

MODEL = Path("/home/samjin/QE/lammps-proj/zeolite/01_models/mace-mh-1.model")
CORPUS = Path(
    "/home/samjin/QE/lammps-proj/zeolite/04_training_dataset/LTA_replay/mh-1/replay_fps_12000.extxyz"
)
WORK = Path(sys.argv[1])
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 128

samples: list[dict] = []


def _nvml() -> tuple[int, int]:
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        used = int(pynvml.nvmlDeviceGetMemoryInfo(handle).used)
        mine = -1
        try:
            for proc in pynvml.nvmlDeviceGetComputeRunningProcesses(handle):
                if int(proc.pid) == os.getpid() and proc.usedGpuMemory:
                    mine = int(proc.usedGpuMemory)
        except Exception:
            mine = -1
        return used, mine
    except Exception:
        try:
            import subprocess

            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True,
            ).stdout.strip().splitlines()[0]
            return int(out) * 1024 * 1024, -1
        except Exception:
            return -1, -1


def sample(label: str) -> dict:
    torch.cuda.synchronize()
    aggregate, mine = _nvml()
    entry = {
        "phase": label,
        "torch_allocated_mib": round(torch.cuda.memory_allocated() / 2**20, 1),
        "torch_reserved_mib": round(torch.cuda.memory_reserved() / 2**20, 1),
        "torch_max_allocated_mib": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        "torch_max_reserved_mib": round(torch.cuda.max_memory_reserved() / 2**20, 1),
        "nvml_device_used_mib": -1 if aggregate < 0 else round(aggregate / 2**20, 1),
        "nvml_this_process_mib": -1 if mine < 0 else round(mine / 2**20, 1),
    }
    samples.append(entry)
    print(json.dumps(entry), flush=True)
    return entry


def _subset(path: Path, frames: list) -> None:
    from ase.io import write

    write(path, frames, format="extxyz")


def cycle(label: str, subset: Path, policy, cache_root: Path, graph_cache: Path) -> dict:
    """One cold build through the production owner, fully instrumented."""

    source = mdstats.inspect_replay_source_extxyz(subset)
    index = mdstats.build_replay_source_index(source, subset.parent / "source-index")
    construct = rp._construct_prediction_provider
    executor_factory = rp._cold_build_inference_executor
    observed = {"providers": 0, "executors": 0, "closes": 0, "caller_closes": 0}

    def traced_construct(policy_arg, source_arg):
        provider = construct(policy_arg, source_arg)
        observed["providers"] += 1
        sample(f"{label}:one_replay_provider_resident")
        return provider

    def traced_executor(provider, **kwargs):
        executor = executor_factory(provider, **kwargs)
        observed["executors"] += 1
        bound_close = executor.close

        def close_and_sample(_close=bound_close):
            # Capture only the bound close, never the executor: a closure that
            # captured the executor and was stored on it would make the
            # instrumentation itself hold model memory the owner released.
            sample(f"{label}:final_consumer_complete_before_close")
            _close()
            observed["closes"] += 1
            sample(f"{label}:explicit_owner_cleanup_returned")

        executor.close = close_and_sample  # type: ignore[method-assign]
        return executor

    rp._construct_prediction_provider = traced_construct
    rp._cold_build_inference_executor = traced_executor
    try:
        cache = mdstats.build_replay_foundation_prediction_cache(
            source, policy, cache_root,
            batch_size=8, shard_size=64,
            graph_cache_directory=graph_cache, source_index=index,
        )
    finally:
        rp._construct_prediction_provider = construct
        rp._cold_build_inference_executor = executor_factory

    print(
        f"[E1] {label}: cache published with {cache.configuration_count} predictions, "
        f"{len(cache.shards)} shards, key={cache.cache_key[:16]}...",
        flush=True,
    )
    assert observed == {"providers": 1, "executors": 1, "closes": 1, "caller_closes": 0}, observed
    # No live provider/executor/model reference may survive in the returned record.
    for field in ("root_directory", "shards", "audit_relative_path"):
        assert not hasattr(getattr(cache, field), "predict_batch"), field
    sample(f"{label}:owner_returned_process_still_alive")
    gc.collect()
    torch.cuda.empty_cache()
    return sample(f"{label}:post_close_after_allocator_release")


def main() -> int:
    from ase.io import iread

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    frames = []
    for atoms in iread(CORPUS, index=":", format="extxyz"):
        frames.append(atoms)
        if len(frames) >= 2 * FRAMES:
            break
    first_dir = WORK / "cycle-a"
    second_dir = WORK / "cycle-b"
    first_dir.mkdir()
    second_dir.mkdir()
    _subset(first_dir / "replay.extxyz", frames[:FRAMES])
    _subset(second_dir / "replay.extxyz", frames[FRAMES:])
    print(f"[E1] two disjoint cold replay subsets of {FRAMES} real frames each", flush=True)

    torch.zeros(1, device="cuda")
    torch.cuda.reset_peak_memory_stats()
    baseline = sample("baseline_context_scale")

    probe = mdstats.inspect_replay_source_extxyz(first_dir / "replay.extxyz")
    potential = MaceFoundationSpec(
        family="mace_mh_1", requested_head="omat_pbe",
        requested_atomic_numbers=tuple(probe.atomic_numbers),
    ).resolve_file(MODEL)
    inference = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32", backend="e3nn", resolved_kernel_mode="e3nn",
        mace_version="e1-proof", adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cuda"
    )
    sample("after_source_and_identity_resolution")

    first = cycle("cycle_a", first_dir / "replay.extxyz", policy,
                  WORK / "foundation-predictions", WORK / "graph-cache")
    second = cycle("cycle_b", second_dir / "replay.extxyz", policy,
                   WORK / "foundation-predictions", WORK / "graph-cache")

    peak = max(s["torch_max_allocated_mib"] for s in samples)
    peak_reserved = max(s["torch_max_reserved_mib"] for s in samples)
    peak_nvml = max(s["nvml_this_process_mib"] for s in samples)
    summary = {
        "baseline_allocated_mib": baseline["torch_allocated_mib"],
        "baseline_reserved_mib": baseline["torch_reserved_mib"],
        "inference_peak_allocated_mib": peak,
        "inference_peak_reserved_mib": peak_reserved,
        "inference_peak_process_nvml_mib": peak_nvml,
        "cycle_a_post_close_allocated_mib": first["torch_allocated_mib"],
        "cycle_b_post_close_allocated_mib": second["torch_allocated_mib"],
        "cycle_a_post_close_reserved_mib": first["torch_reserved_mib"],
        "cycle_b_post_close_reserved_mib": second["torch_reserved_mib"],
        "cycle_a_post_close_process_nvml_mib": first["nvml_this_process_mib"],
        "cycle_b_post_close_process_nvml_mib": second["nvml_this_process_mib"],
        "process_alive": True,
    }
    print(json.dumps({"summary": summary}, indent=2), flush=True)

    # 1. The model-scale owner is gone: post-close residency is a small fraction
    #    of the inference high-water, not the provider-plus-peak residency the
    #    unretired path left behind.
    assert second["torch_allocated_mib"] <= 0.05 * peak, summary
    assert second["torch_reserved_mib"] <= 0.20 * peak_reserved, summary
    # 2. It is *retirement*, not a smaller leak: a second full cold build with
    #    its own provider and its own inference adds nothing durable.
    assert second["torch_allocated_mib"] <= first["torch_allocated_mib"], summary
    assert second["torch_reserved_mib"] <= first["torch_reserved_mib"], summary
    assert second["nvml_this_process_mib"] <= first["nvml_this_process_mib"], summary
    print(
        "[E1] PASS: one provider per cold build, exactly one explicit retirement, "
        "bounded non-accumulating post-close residency, process still alive",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
