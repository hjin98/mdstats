---
title: "MLFF PERF-P3 CPU Benchmark Evidence"
version: "0.20.185a0"
date: "2026-08-15"
status: "bounded CPU qualification; GPU qualification deferred to FINAL-GPU1"
geometry: margin=0.85in
---

# Scope

PERF-P3 is an execution-equivalent CPU hardening gate. This report records matched CPU evidence for the direct local-structure kernel, exact FOUNDATION-AUDIT1 temporary-memory handling, and rejected candidate optimizations. Accelerator evidence is intentionally deferred to `FINAL-GPU1`.

# Host

The bounded cloud host exposed an AMD EPYC 9V74 processor, nine logical CPUs, an 8-core cgroup quota, and a 4 GiB memory limit. The structural microbenchmark fixes native BLAS/OpenMP work to one thread per fresh process so it measures the per-worker kernel rather than scheduler-dependent nested parallelism.

# Direct structural kernel

The fixture uses a deterministic triclinic, fixed-topology, LTA-like system with 168 atoms and 300 frames. Three fresh-process samples were collected for each path.

| Metric | `0.20.184a0` | PERF-P3 | Change |
|---|---:|---:|---:|
| Median wall time | 3.458792 s | 3.202054 s | **7.42% lower** |
| Wall-time range | 3.331898-3.676044 s | 3.193411-3.390388 s | - |
| Median peak RSS | 270.35 MiB | 270.33 MiB | effectively unchanged |

Every sample produced the exact same numerical digest:

`5786409f8f622b3e2d1183bcca9ef9859e3cfd7717970339f421d4f630d6ac4c`

The qualified change therefore removes wrapper/allocation overhead without changing feature bytes.

# Foundation-audit temporary memory

The audit fixture contains 600 frames with 1,500 atoms each, for 900,000 atoms total. It exercises the actual exact force-tail reduction while replacing prediction I/O with deterministic in-memory inputs.

| Path | Wall time | Peak RSS | Scientific digest |
|---|---:|---:|---|
| Pre-P3 list + concatenate | 0.157148 s | 346.18 MiB | identical |
| P3 exact preallocation | 0.192061 s | 318.41 MiB | identical |
| P3 forced mmap | 0.206037 s | 318.46 MiB | identical |

Preallocation reduces measured peak RSS by **8.02%**. It is not promoted as a speed optimization: the measured in-memory wall time is 22.22% higher on this deliberately reduction-heavy microfixture. The mmap path is a bounded-allocation fallback; quantile evaluation still touches mapped pages, so mmap is not claimed to reduce resident memory further in this fixture.

All three paths produced:

`a618301c7f8dad6f5cd8cfec4d39edea9303b5c2f1c52bf46b81507677808f9f`

# Rejected optimizations

Two candidates were deliberately rejected. Retaining dense reusable pair/radial scratch increased RSS and reduced throughput. Chunking the radial-channel reduction changed FP64 values at approximately $10^{-16}$ to $8.9	imes10^{-16}$, so it was rejected even though the differences are numerically tiny: PERF-P3 is Class E and requires exact scientific identity.

# Interpretation

The bounded authority supports a **7.42% median per-worker structural-kernel wall-time reduction** and an **8.02% audit peak-RSS reduction**. It does not support a GPU claim, a full-corpus end-to-end speedup claim, or a claim that mmap lowers RSS under every access pattern.
