# Replay Provider Lifetime and Stage Ownership Qualification (E1 & E2)

This directory contains target-host evidence proving provider retirement and stage ownership boundaries across the single-source MACE replay pipeline.

**Target Host:** Local workstation with NVIDIA GeForce RTX 3090 (24 GiB VRAM), 32 CPU cores.
**Runtime:** Conda environment `mace`, Python 3.11, PyTorch 2.13.0+cu126, mace-torch 0.3.16.

---

## E1: Replay Provider Retirement Proof

`e1_replay_provider_retirement_proof.py` drives `build_replay_foundation_prediction_cache` with `provider=None`, so the owner constructs the provider, transfers ownership once to the operation-scoped executor, and retires it in its own `finally` block against the real MH-1 checkpoint (`01_models/mace-mh-1.model`) and real replay corpus (`04_training_dataset/LTA_replay/mh-1/replay_fps_12000.extxyz`) in a Python process that remains alive after return.

It runs **two** disjoint cold builds to distinguish retirement from memory accumulation: a second full build with its own provider and inference adds zero durable residency.

### Reproduction

```bash
conda run -n mace python qualification/replay-provider-lifetime/e1_replay_provider_retirement_proof.py <scratch-dir> 128
```

Evidence file: `E1_REPLAY_PROVIDER_RETIREMENT_EVIDENCE.txt`

### Key Results
- Baseline allocated: 0.0 MiB (reserved: 2.0 MiB)
- Inference peak allocated: 1437.6 MiB (reserved: 2920.0 MiB, process NVML: 3238.0 MiB)
- Cycle 1 (A) post-close allocated: 16.2 MiB (reserved: 216.0 MiB, process NVML: 534.0 MiB)
- Cycle 2 (B) post-close allocated: 16.2 MiB (reserved: 216.0 MiB, process NVML: 534.0 MiB) — identical to Cycle 1, zero leak.
- Post-close allocated is only 1.1% of inference peak (16.2 MiB / 1437.6 MiB), with the process remaining alive.

---

## E2: Assembled CLI Stage Proof (`doctor -> prepare -> P5 -> pre-TRAIN2`)

`e2_assembled_cli_stage_proof.py` executes the full public CLI pipeline for a single-source `foundation_pseudolabel` campaign on target-host CUDA hardware:

1. **Stage 1 (Doctor):** Runs `cli.command_doctor`. Asserts zero replay provider construction, zero foundation inference, and zero mutable replay aliases published.
2. **Stage 2 (Prepare):** Runs `ctsr.execute_current_prepare`. Asserts exactly one provider construction, one executor construction, one executor close, exactly 128 predictions evaluated, cache published, and post-prepare CUDA memory drops to baseline (< 2.1% of peak).
3. **Stage 3 (P5 Post-Selection Resolution):** Resolves post-selection replay authority via `_resolve_post_selection_replay_resolution(..., require_train=True)`. Asserts read-only consumption: zero new provider constructs, zero new predictions, and identical `lineage_digest`.
4. **Stage 4 (Pre-TRAIN2 Scheduler Observation):** Runs `build_training_concurrency_plan` against live GPU telemetry. Asserts baseline VRAM is clean (~1.3 GiB), initial/ceiling jobs >= 1, and `zero_safe_admission` is `False`.

### Reproduction

```bash
conda run -n mace python qualification/replay-provider-lifetime/e2_assembled_cli_stage_proof.py <scratch-dir> 128
```

Evidence file: `E2_ASSEMBLED_CLI_STAGE_EVIDENCE.txt`

### Summary Metrics from Verified Run
```json
{
  "e2_qualification_summary": {
    "host_gpu": "NVIDIA GeForce RTX 3090",
    "total_vram_gib": 23.55,
    "frames_evaluated": 128,
    "doctor_provider_constructs": 0,
    "doctor_predictions": 0,
    "doctor_published_aliases": 0,
    "prepare_provider_constructs": 1,
    "prepare_executor_constructs": 1,
    "prepare_executor_closes": 1,
    "prepare_predictions": 128,
    "prepare_cache_key": "b9f3b040b614956ff7715bd52d16a58fe0a934a94fe83312b8d3c7425f28cbb9",
    "prepare_shards": 2,
    "inference_peak_allocated_mib": 2198.2,
    "inference_peak_reserved_mib": 2864.0,
    "post_prepare_allocated_mib": 45.9,
    "post_prepare_reserved_mib": 122.0,
    "p5_lineage_digest": "3298ba6383ddeb89b30bbd7a6a40b3bd8bd0dfbf80ebd30b28fb5aacc80a323d",
    "p5_split_manifest_digest": "e67b6156896201da480f54e1156d73a957465536a0505cff271e3442525470a5",
    "p5_source_sha256": "4f0a4c2fc2007b11ead0088c34bfa8cb92afea38f69f110a48384af775b3b37d",
    "p5_new_predictions": 0,
    "p5_new_providers": 0,
    "scheduler_baseline_vram_gib": 1.44,
    "scheduler_admission_ceiling_jobs": 1,
    "candidate_commit": "71a9b9f4f2217c6e102d41e8245b04cc183f15e2",
    "candidate_tree": "c2c0001c81ded4b9eccfe768825a0adeec536e1d",
    "candidate_clean": true,
    "overall_verdict": "PASS"
  }
}
```
