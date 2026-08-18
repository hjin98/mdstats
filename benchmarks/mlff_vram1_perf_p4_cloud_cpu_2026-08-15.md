---
title: "VRAM1 + PERF-P4 Bounded CPU Control-Plane Benchmark"
date: "2026-08-15"
geometry: margin=0.85in
---

# Scope

This benchmark measures only CPU-side DATA6 orchestration. It does **not** qualify CUDA memory capacity, VRAM reserve, host-to-device overlap, or GPU throughput. Those measurements remain in `FINAL-GPU1`.

Host: AMD EPYC 9V74; 9 logical CPUs visible. Release: `mdstats 0.20.186a0`.

# Fixture

The deterministic production-sweep fixture contains 44 requested frames. Both modes use batch size 4, artifact shard size 3, and persistence queue depth 1. Fifteen repetitions per mode are run in alternating order.

Scientific signature for every repetition:

`c07e1bb049703c0b160b88b18bfa0c6c0c788198cf21a6d0454ef9c19c689a96`

# Results

| Mode | Median wall | Range | Median process CPU | Median write chars |
|---|---:|---:|---:|---:|
| Synchronous | 72.89 ms | 65.84-79.10 ms | 45.57 ms | 339,873 |
| Bounded pipeline | 76.32 ms | 68.47-115.99 ms | 50.36 ms | 339,873 |

The bounded pipeline is **4.72% slower** on this small CPU-only fixture. That result is expected to be dominated by executor/queue overhead because no accelerator work is available to hide. It is retained as negative performance evidence rather than converted into a speedup claim.

# Interpretation

PERF-P4 passes its CPU/reference objective: synchronous and pipelined execution are scientifically identical, queueing is bounded, and synchronous fallback remains available. The performance acceptance question is intentionally unresolved until `FINAL-GPU1`, where graph preparation and persistence can overlap real accelerator inference.

Machine-readable evidence: `benchmarks/mlff_vram1_perf_p4_cloud_cpu_2026-08-15.json`.
