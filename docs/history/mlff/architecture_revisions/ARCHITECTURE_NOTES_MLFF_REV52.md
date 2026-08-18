---
title: "MLFF Architecture Revision 52"
version: "0.20.185a0"
date: "2026-08-15"
status: "PERF-P3 CPU structural/reduction hardening implemented"
geometry: margin=0.85in
---

# Revision 52

Revision 52 implements **PERF-P3** as an Authority-Class-E CPU hardening gate and advances the implementation roadmap to **VRAM1 + PERF-P4**. Accelerator qualification remains consolidated under `FINAL-GPU1`.

## Direct structural execution

DATA6 no longer constructs a one-frame `AtomisticFrameCollection` for each local-structure call. It reuses immutable per-topology chemistry arrays and calls the exact array kernel directly. Worker-local scratch is deliberately limited to wrapped fractional coordinates. Larger pair/radial scratch and a chunked radial reduction were tested and rejected because the former regressed RSS/throughput and the latter altered FP64 bytes.

## Audit memory

FOUNDATION-AUDIT1 now determines exact final force-tail lengths and fills preallocated arrays. Large temporary arrays may use an execution-only mmap threshold. In-memory and mmap paths reproduce identical audit authority.

## Resource scopes

A stage-local resource scope now provides one admission budget across Python concurrency, structural workers, cKDTree workers, BLAS/OpenMP threads, PyTorch CPU workers, and GPU-job count. Oversubscribed combinations fail before execution; effective counts remain telemetry only.

## Bounded evidence

The controlled 168-atom/300-frame structural fixture improves median wall time from 3.458792 s to 3.202054 s (**7.42%**), with identical digest `5786409f8f622b3e2d1183bcca9ef9859e3cfd7717970339f421d4f630d6ac4c`. The 900,000-atom audit fixture reduces peak RSS from 346.18 MiB to 318.41 MiB (**8.02%**) with identical audit digest. No end-to-end GPU or full-corpus speed claim is made.

## Next gate

**VRAM1 + PERF-P4** is next. GPU qualification remains deferred to the final release package.
