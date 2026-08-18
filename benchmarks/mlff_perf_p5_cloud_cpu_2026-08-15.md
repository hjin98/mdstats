---
title: "MLFF PERF-P5 CPU Persistence Benchmark"
date: "2026-08-15"
documentclass: extarticle
geometry: margin=0.68in
fontsize: 9pt
---

# Environment

- CPU: AMD EPYC 9V74 80-Core Processor
- Visible logical CPUs: 9
- cgroup CPU quota: 8 cores
- cgroup memory limit: 4 GiB
- Python: 3.13.5
- PyTorch: 2.10.0+cpu
- Tensor fixture: 64,000,000 FP32 values = 256,000,000 bytes

# Streamed hashing

Each path was run in a fresh process. The tensor allocation occurs before the measured digest interval. Peak-RSS increment therefore isolates additional hashing residency rather than the tensor itself.

| Digest path | Samples (s) | Median | Peak-RSS increment |
|---|---|---:|---:|
| TRAIN2 legacy `tobytes()` | 0.27989, 0.25014 | 0.26502 s | 245.00 MiB |
| TRAIN2 streamed buffer | 0.14235, 0.14360 | 0.14297 s | 0.75 MiB |
| STOR2 legacy `tobytes()` | 0.25330, 0.24309 | 0.24819 s | 244.94 MiB |
| STOR2 streamed buffer | 0.15128, 0.14246 | 0.14687 s | 0.81 MiB |

TRAIN2 wall time is **46.05% lower** and STOR2 capsule hashing is **40.82% lower** on this fixture. Both streamed paths remove approximately 244 MiB of transient peak residency.

Scientific digests are unchanged:

- TRAIN2: `c5e22dcc6fd8646fee9c6bdce424d59029abd5dbb286b0e353fceea3ec5568ca`
- STOR2: `bd118d11da1689dd6b8f0c9a865b85a83cbf188686f9a54ee028430f1af716ad`

# Optional EVAL2 model shell

The supplied MACE-MH-1/`omat_pbe` model was loaded three times through each CPU path after runtime warm-up.

| Path | Samples (s) | Median |
|---|---|---:|
| Fresh MACE calculator | 0.09796, 0.09886, 0.10937 | 0.09886 s |
| Same-architecture state reload | 0.10245, 0.10815, 0.10528 | 0.10528 s |

State reload is **6.49% slower** on this CPU path. Predictions before/after reload and against fresh construction are byte-identical. The shell interface is therefore retained as an optional accelerator experiment, not a CPU default.

# Interpretation

PERF-P5's qualified benefit is late persistence hashing: lower transient memory and lower hashing wall time with exactly unchanged byte identities. No GPU throughput claim is made. No HDF5/LMDB conversion or restart-state reduction is part of this gate.
