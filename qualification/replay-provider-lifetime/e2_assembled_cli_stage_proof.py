"""E2 - assembled CLI stage proof: doctor -> prepare -> P5 -> pre-TRAIN2.

Drives the assembled production CLI route with explicit `foundation_pseudolabel`
on the real MH-1 checkpoint and real selected replay corpus on an NVIDIA RTX 3090 GPU:
1. Doctor: validates only, performs ZERO replay foundation inference, and publishes no replay alias.
2. Prepare: the sole expensive pseudo realization owner; runs single-flight GPU inference,
   publishes current replay authority, and explicitly retires the provider/executor before return.
3. P5: consumes the prepared replay authority strictly read-only (zero provider, zero inference).
4. Pre-TRAIN2 CV Scheduler: observes clean baseline GPU memory with zero prepare-owned model-scale residency,
   confirming healthy admission headroom.
"""
from __future__ import annotations

import gc
import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
from ase.io import iread, write

import mdstats
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_target_size_runtime as ctsr
from mdstats.training_data import replay_pseudolabel as rp
from mdstats.training_data.campaign_post_selection_runtime import (
    _post_selection_training_concurrency_policy,
    _resolve_post_selection_replay_resolution,
)
from mdstats.training_data.post_selection_identity import compute_replay_lineage_digest
from mdstats.training_data.training_parallel import (
    build_training_concurrency_plan,
    query_gpu_telemetry,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

MODEL = Path("/home/samjin/QE/lammps-proj/zeolite/01_models/mace-mh-1.model")
CORPUS = Path(
    "/home/samjin/QE/lammps-proj/zeolite/04_training_dataset/LTA_replay/mh-1/replay_fps_12000.extxyz"
)
WORK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/e2_assembled_proof")
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


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    import subprocess
    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), check=True,
        ).stdout.strip()
        git_tree = subprocess.run(
            ["git", "write-tree"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), check=True,
        ).stdout.strip()
        porcelain = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), check=True,
        ).stdout.strip()
        lines = [
            line for line in porcelain.splitlines()
            if not line.strip().endswith("E2_ASSEMBLED_CLI_STAGE_EVIDENCE.txt")
        ]
        git_clean = (len(lines) == 0)
    except Exception:
        git_commit, git_tree, git_clean = "unknown", "unknown", False

    print(f"[E2] Host GPU: {torch.cuda.get_device_name(0)} ({torch.cuda.get_device_properties(0).total_memory / 2**30:.1f} GiB)")
    print(f"[E2] Candidate provenance: commit={git_commit} tree={git_tree} clean={git_clean}")
    print(f"[E2] Preparing {FRAMES} real frames from {CORPUS.name}...", flush=True)

    frames = []
    for atoms in iread(CORPUS, index=":", format="extxyz"):
        frames.append(atoms)
        if len(frames) >= FRAMES:
            break
    replay_source = WORK / "replay.extxyz"
    write(replay_source, frames, format="extxyz")

    config_path, workspace_path = p4d._fixture_campaign(WORK)
    text = config_path.read_text()
    text = text.replace(
        "[paths]",
        f'[paths]\nfoundation_model = "{MODEL}"\nreplay_set = "{replay_source}"',
    )
    text = text.replace(
        'profile = "generic"',
        'profile = "generic"\nmode = "multihead_replay"',
    )
    text = text.replace(
        'device = "cpu"',
        'device = "cuda"',
    )
    text += """
[execution]
minimum_free_disk_gib = 1.0

[foundation]
family = "mace_mh_1"
head = "omat_pbe"

[replay]
label_mode = "foundation_pseudolabel"
split_ratio = "4:1"
split_seed = 42
prediction_batch_size = 16
prediction_shard_size = 64
minimum_train_configurations = 1
minimum_monitor_configurations = 1
require_target_elements = false
allow_small_corpus = true
"""
    config_path.write_text(text, encoding="utf-8")
    cfg, paths = cli._load_config(config_path)

    torch.zeros(1, device="cuda")
    torch.cuda.reset_peak_memory_stats()
    baseline = sample("baseline_clean_device")

    # Instrument provider construction, executor lifecycle, and batch inference
    observed = {
        "provider_constructs": 0,
        "executor_constructs": 0,
        "executor_closes": 0,
        "predictions_made": 0,
    }

    orig_construct = rp._construct_prediction_provider
    orig_executor = rp._cold_build_inference_executor

    def traced_construct(policy_arg, source_arg):
        observed["provider_constructs"] += 1
        return orig_construct(policy_arg, source_arg)

    def traced_executor(provider, **kwargs):
        observed["executor_constructs"] += 1
        executor = orig_executor(provider, **kwargs)
        bound_close = executor.close
        bound_predict = executor.predict

        def traced_predict(atoms, *a, **k):
            observed["predictions_made"] += len(atoms)
            return bound_predict(atoms, *a, **k)

        def traced_close():
            observed["executor_closes"] += 1
            sample("prepare:executor_close_called")
            bound_close()
            sample("prepare:executor_close_completed")

        executor.predict = traced_predict  # type: ignore[method-assign]
        executor.close = traced_close  # type: ignore[method-assign]
        return executor

    rp._construct_prediction_provider = traced_construct
    rp._cold_build_inference_executor = traced_executor

    # -----------------------------------------------------------------------
    # Stage 1: Assembled Doctor
    # -----------------------------------------------------------------------
    print("\n[E2] === Stage 1: Doctor ===", flush=True)
    sample("doctor:before")
    args_doctor = SimpleNamespace(config=str(config_path))
    rc_doctor = cli.command_doctor(args_doctor)
    sample("doctor:after")

    assert rc_doctor == 0, f"doctor failed with return code {rc_doctor}"
    assert observed["provider_constructs"] == 0, "doctor constructed a replay provider!"
    assert observed["predictions_made"] == 0, "doctor performed replay inference!"

    store = cli.CampaignStore(paths.state_db)
    try:
        doctor_stage, doctor_msg = store.stage("doctor")
        assert doctor_stage is cli.StageState.COMPLETE, f"doctor stage state: {doctor_stage}"
        # Doctor must publish zero replay alias records
        replay_records = [k for k in store.record_keys("replay_") if not k.startswith("replay_plan_doctor")]
        assert len(replay_records) == 0, f"doctor published replay aliases: {replay_records}"
    finally:
        store.close()

    print("[E2] Doctor PASS: validated campaign and environment, 0 foundation predictions, 0 replay aliases.", flush=True)

    # -----------------------------------------------------------------------
    # Stage 2: Assembled Prepare
    # -----------------------------------------------------------------------
    print("\n[E2] === Stage 2: Prepare ===", flush=True)
    sample("prepare:before")
    args_prepare = SimpleNamespace(
        config=str(config_path),
        approve_manifest=False,
        refresh_inferences=False,
        rebuild_catalog=False,
    )
    rc_prepare = ctsr.execute_current_prepare(args_prepare)
    sample("prepare:after_return")

    assert rc_prepare == 0, f"prepare failed with return code {rc_prepare}"
    assert observed["provider_constructs"] == 1, f"expected 1 provider construction, got {observed['provider_constructs']}"
    assert observed["executor_constructs"] == 1, f"expected 1 executor construction, got {observed['executor_constructs']}"
    assert observed["executor_closes"] == 1, f"expected 1 executor close, got {observed['executor_closes']}"
    assert observed["predictions_made"] == FRAMES, f"expected {FRAMES} predictions, got {observed['predictions_made']}"

    store = cli.CampaignStore(paths.state_db)
    try:
        prepare_stage, prepare_msg = store.stage("prepare")
        assert prepare_stage is cli.StageState.COMPLETE, f"prepare stage state: {prepare_stage}"
        lineage_payload = store.get_payload("replay_current_lineage")
        qual_payload = store.get_payload("replay_qualification")
        assert lineage_payload.get("replay_lineage_digest"), "missing replay_lineage_digest"
        assert qual_payload.get("qualified") is True, "replay is not qualified"

        # Record cache disposition
        pred_record = store.get_payload("replay_foundation_prediction_cache")
        cache_dir = Path(pred_record["root_directory"])
        cache_key = pred_record["cache_key"]
        cache_shards = pred_record["shards"]
        cache_count = pred_record["configuration_count"]
    finally:
        store.close()

    gc.collect()
    torch.cuda.empty_cache()
    post_prepare = sample("prepare:post_gc_and_empty_cache")

    peak_allocated = max(s["torch_max_allocated_mib"] for s in samples)
    peak_reserved = max(s["torch_max_reserved_mib"] for s in samples)

    print(
        f"[E2] Prepare cache disposition: dir={cache_dir}, key={cache_key[:16]}..., "
        f"shards={len(cache_shards)}, predictions={cache_count}",
        flush=True,
    )
    # Assert model-scale provider was retired: post-prepare allocated memory is a small fraction of peak
    assert post_prepare["torch_allocated_mib"] <= 0.05 * peak_allocated, (
        f"post_prepare allocated {post_prepare['torch_allocated_mib']} MiB > 5% of peak {peak_allocated} MiB"
    )
    print("[E2] Prepare PASS: single-flight inference, cache published, provider retired, clean post-prepare memory.", flush=True)

    # -----------------------------------------------------------------------
    # Stage 3: P5 Post-Selection Replay Resolution (Read-Only Consumer)
    # -----------------------------------------------------------------------
    print("\n[E2] === Stage 3: P5 Post-Selection Replay Resolution ===", flush=True)
    sample("p5:before")
    pre_p5_predictions = observed["predictions_made"]
    pre_p5_providers = observed["provider_constructs"]

    p5_context = SimpleNamespace(cfg=cfg, paths=paths)
    resolution = _resolve_post_selection_replay_resolution(p5_context, require_train=True)
    sample("p5:after")

    assert resolution is not None, "P5 replay resolution returned None"
    assert observed["provider_constructs"] == pre_p5_providers, "P5 constructed a provider (must be read-only!)"
    assert observed["predictions_made"] == pre_p5_predictions, "P5 made foundation predictions (must be read-only!)"

    p5_lineage_digest = compute_replay_lineage_digest(resolution)
    print("P5 resolution identities:", flush=True)
    print(f"  source_path: {resolution.source_path}", flush=True)
    print(f"  source_content_digest: {resolution.source_content_digest[:16]}...", flush=True)
    print(f"  source_sha256: {resolution.source_sha256[:16]}...", flush=True)
    print(f"  split_manifest_digest: {resolution.split_manifest_digest[:16]}...", flush=True)
    print(f"  lineage_digest: {p5_lineage_digest[:16]}...", flush=True)

    assert p5_lineage_digest == lineage_payload["replay_lineage_digest"], (
        f"P5 lineage digest {p5_lineage_digest} != published lineage {lineage_payload['replay_lineage_digest']}"
    )
    print("[E2] P5 PASS: read-only consumption of prepared authority, zero inference, matching lineage digest.", flush=True)

    # -----------------------------------------------------------------------
    # Stage 4: Pre-TRAIN2 CV Scheduler Memory Observation
    # -----------------------------------------------------------------------
    print("\n[E2] === Stage 4: Pre-TRAIN2 CV Scheduler Observation ===", flush=True)
    scheduler_sample = query_gpu_telemetry("cuda")
    resources = cli._performance_resources(cfg)
    concurrency_policy = _post_selection_training_concurrency_policy(p5_context)
    concurrency_plan = build_training_concurrency_plan(
        task_count=1,
        device="cuda",
        loader_workers_per_job=0,
        resources=resources,
        policy=concurrency_policy,
        gpu_sample=scheduler_sample,
    )
    sample("scheduler:concurrency_plan_built")

    print(f"[E2] Concurrency plan summary: {concurrency_plan.summary()}", flush=True)
    print(f"[E2] Zero safe admission: {concurrency_plan.zero_safe_admission}", flush=True)

    assert concurrency_plan.baseline_gpu_used_bytes is not None, "scheduler observed no baseline GPU memory"
    assert concurrency_plan.zero_safe_admission is False, "zero_safe_admission was triggered unexpectedly"
    assert concurrency_plan.initial_jobs >= 1, f"expected initial_jobs >= 1, got {concurrency_plan.initial_jobs}"

    # Verify no prepare-owned model-scale CUDA residency in the process
    assert post_prepare["torch_allocated_mib"] <= 0.05 * peak_allocated

    summary = {
        "host_gpu": torch.cuda.get_device_name(0),
        "total_vram_gib": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2),
        "frames_evaluated": FRAMES,
        "doctor_provider_constructs": 0,
        "doctor_predictions": 0,
        "doctor_published_aliases": 0,
        "prepare_provider_constructs": observed["provider_constructs"],
        "prepare_executor_constructs": observed["executor_constructs"],
        "prepare_executor_closes": observed["executor_closes"],
        "prepare_predictions": observed["predictions_made"],
        "prepare_cache_key": cache_key,
        "prepare_shards": len(cache_shards),
        "inference_peak_allocated_mib": peak_allocated,
        "inference_peak_reserved_mib": peak_reserved,
        "post_prepare_allocated_mib": post_prepare["torch_allocated_mib"],
        "post_prepare_reserved_mib": post_prepare["torch_reserved_mib"],
        "p5_lineage_digest": p5_lineage_digest,
        "p5_split_manifest_digest": resolution.split_manifest_digest,
        "p5_source_sha256": resolution.source_sha256,
        "p5_new_predictions": 0,
        "p5_new_providers": 0,
        "scheduler_baseline_vram_gib": round(concurrency_plan.baseline_gpu_used_bytes / (1024**3), 2),
        "scheduler_admission_ceiling_jobs": concurrency_plan.maximum_jobs,
        "candidate_commit": git_commit,
        "candidate_tree": git_tree,
        "candidate_clean": git_clean,
        "overall_verdict": "PASS",
    }
    print("\n" + json.dumps({"e2_qualification_summary": summary}, indent=2), flush=True)
    print("\n[E2] PASS: doctor -> prepare -> P5 -> pre-TRAIN2 verified cleanly on target host hardware.", flush=True)

    # Restore uninstrumented methods
    rp._construct_prediction_provider = orig_construct
    rp._cold_build_inference_executor = orig_executor
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
