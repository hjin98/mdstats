---
title: "mdstats 0.20.187a0"
subtitle: "PERF-P5 TRAIN2/EVAL2 persistence and reuse hardening"
author: "mdstats development"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    \usepackage{microtype}
---

# `mdstats 0.20.187a0`

This release closes the CPU/control-plane portion of **PERF-P5**. It preserves TRAIN2 restart state, STOR2 capsule identity, EVAL2 scientific metrics, checkpoint ranking, and generated defaults.

## Changes

- Stream canonical contiguous CPU tensor bytes directly into SHA-256 in bounded chunks for TRAIN2 and STOR2 state hashing. The historical digest byte contract is unchanged.
- Add execution-only `train2_persistence.jsonl` telemetry for clone, hash, write, summary, total time, and payload sizes.
- Add a strictly optional EVAL2 compatible-model state reload path. Exact model class, key set, tensor shape and tensor dtype compatibility are mandatory; `load_state_dict(..., strict=True)` remains the final application check.
- Keep fresh EVAL2 model reconstruction as the default. The supplied MH-1 CPU/e3nn test is exact but shell reload is 6.49% slower on this host.
- Keep MACE HDF5/LMDB as dataset formats rather than relabeling them as authenticated graph caches.
- Advance the canonical architecture to revision 54 and dependency-graph schema 36.

## Bounded CPU evidence

A 256 MB contiguous FP32 state gives the following medians from two fresh-process samples per path:

| Path | Pre-P5 | PERF-P5 | Wall reduction | Extra peak RSS reduction |
|---|---:|---:|---:|---:|
| TRAIN2 state hash | 265.02 ms | 142.97 ms | 46.05% | 99.69% |
| STOR2 capsule hash | 248.19 ms | 146.87 ms | 40.82% | 99.67% |

TRAIN2 digest:

`c5e22dcc6fd8646fee9c6bdce424d59029abd5dbb286b0e353fceea3ec5568ca`

STOR2 capsule digest:

`bd118d11da1689dd6b8f0c9a865b85a83cbf188686f9a54ee028430f1af716ad`

Both match the legacy implementation exactly.

## Qualification boundary

No accelerator claim is made in this release. GPU-side checkpoint persistence, shell reuse, synchronization overhead, VRAM impact, and end-to-end TRAIN2/EVAL2 throughput remain part of the final consolidated **FINAL-GPU1** handoff.
