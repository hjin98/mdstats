---
title: "MLFF Architecture Revision 84"
subtitle: "CUEQ-REPEAT1-DIAG2 full self-tail and deterministic-control refinement"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.8in
fontsize: 10pt
---

# Revision 84

**Release:** `mdstats 0.20.217a0`  
**Dependency-graph schema:** 66  
**Gate:** `CUEQ-REPEAT1-DIAG2`

The MPA-0/default 10-repeat workstation evidence showed e3nn-self `Fmax` max `2.120e-5`, CuEq-self max `2.076e-5`, and paired e3nn/CuEq max `1.699e-5`, with paired `Frmse` only `2.023e-6` to `3.374e-6` and identical selection in 10/10 repeats. Same-backend noise therefore exceeds the observed cross-backend extreme-value discrepancy.

Revision 84 keeps the active TRAIN2 FP32 parity policy unchanged at `rtol=1e-5, atol=1e-5` and refines measurement only. Ordinary doctor output now prints e3nn-self and CuEq-self `Fmax`, `Frmse`, `Fp99`, `Fp99.9`, and counts above `1e-5`, in addition to the existing paired cross-backend statistics.

A second isolated deterministic-control subprocess is added. Before CUDA initialization it sets the CUBLAS deterministic workspace to `:4096:8`, enables deterministic PyTorch algorithms with error-mode diagnostics, disables cuDNN benchmarking, and enables deterministic cuDNN execution. It repeats the same 10-run probe. Successful controls print a complete `[DIAG-DET]` block; unsupported nondeterministic operations print and persist their exact failure without fallback.

Both ordinary and deterministic-control measurements remain non-authorizing. The revision-82 FINAL-GPU1/HF2 handoff remains archival until the measured distributions are interpreted and a final noise-normalized parity criterion is frozen.
