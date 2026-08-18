---
title: "mdstats 0.20.186a0 Patch Notes"
date: "2026-08-15"
geometry: margin=0.85in
---

# `mdstats 0.20.186a0`

This release implements **VRAM1 + PERF-P4** while keeping all GPU qualification deferred to `FINAL-GPU1`.

## VRAM1

- Adds `MaceBatchCapacityCalibration.v2` and per-probe capacity evidence.
- Calibrates the actual descriptor/prediction/combined DATA6 workload.
- Uses deterministic stress-oriented graph/atom sampling instead of first-frame sampling.
- Records allocator and driver-visible CUDA memory state, throughput, absolute reserve, and fractional headroom.
- Performs one post-calibration cleanup and a fresh live-VRAM clamp before execution.
- Persists identity-bound OOM safe caps for restart reuse.
- Accounts for graph, descriptor, and prediction host residency.

Historical v1 calibration records remain readable as descriptor-only evidence.

## PERF-P4

- Adds native CPU graph prefetch for the next combined MACE batch.
- Adds bounded asynchronous descriptor/prediction shard persistence.
- Preserves plan order, payload-before-journal commit ordering, restart semantics, and synchronous fallback.
- Rejects persistence queue depths outside one or two.
- Leaves pinned/nonblocking transfer disabled until final GPU benchmarking demonstrates a benefit.

## Qualification

The supplied MH-1 and MPA-0 models match exactly between direct and prepared CPU/e3nn combined-batch execution. Synchronous and pipelined DATA6 execution also produce identical scientific authority on the bounded 44-frame fixture.

On this CPU-only host the pipeline median is 76.32 ms versus 72.89 ms synchronous, a 4.72% overhead. No pipeline speedup or VRAM claim is made. CUDA/VRAM and accelerator-throughput acceptance is deferred to `FINAL-GPU1`.

Architecture revision: **53**. Dependency graph schema: **35**. Next CPU/control-plane implementation gate: **PERF-P5**.
