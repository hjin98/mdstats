---
title: "MLFF Architecture Revision 53"
version: "0.20.186a0"
date: "2026-08-15"
status: "VRAM1 + PERF-P4 CPU/control-plane implementation complete; accelerator acceptance deferred"
geometry: margin=0.85in
---

# Revision 53

Revision 53 implements **VRAM1 + PERF-P4** without interrupting development for GPU qualification. Accelerator-memory and throughput acceptance remains scheduled under `FINAL-GPU1`; **PERF-P5** becomes the next CPU/control-plane implementation gate.

## Capacity evidence

`MaceBatchCapacityCalibration.v2` now measures the actual descriptor, prediction, or combined DATA6 workload. It binds deterministic stress-frame identities, per-probe throughput, CUDA allocated/reserved peaks, driver free/total memory, absolute/fractional headroom, host-residency estimates, and post-cleanup state. Historical v1 remains readable with descriptor-only semantics.

A calibrated cap is only a prior. DATA6 re-clamps it against fresh live VRAM before execution. Runtime OOM backoff is durable and identity-bound, so a matching restart reuses the learned safe cap while changed model/policy/device/workload/calibration identity invalidates it.

## Bounded execution pipeline

Native MACE combined evaluation can prebuild batch $n+1$ on CPU while batch $n$ is evaluated, and shard persistence can overlap behind both. Queues are bounded and included in host-memory admission. Persistence completion never changes scientific order; the append-only journal and ordered compaction remain recovery authority. Synchronous execution is retained as an exact fallback.

Pinned/nonblocking transfers are not promoted without accelerator evidence. This follows PyTorch's documented workload-dependent transfer behavior and preserves the project rule that execution optimizations must be measured rather than assumed.

## Reference qualification

The supplied MH-1/`omat_pbe` and MPA-0-medium/`default` CPU/e3nn prepared and direct combined-evaluation paths are byte-identical on locked regression structures. The bounded 44-frame DATA6 fixture also yields one identical scientific signature under synchronous and pipelined orchestration. The pipeline is 4.72% slower on that tiny CPU-only fixture, so no CPU speedup claim is made.

## Qualification boundary

The development host cannot qualify CUDA peak/reserved memory, OOM capacity, transfer overlap, or accelerator throughput. Those items remain explicit `FINAL-GPU1` obligations. This release therefore records VRAM1/PERF-P4 as **implemented and CPU/control-plane qualified, accelerator qualification pending**.

## Next implementation gate

**PERF-P5** is next. Its CPU/control-plane implementation may proceed before the deferred E3NN-BASELINE campaign; final performance qualification remains conditional on the release-matched GPU baseline.
