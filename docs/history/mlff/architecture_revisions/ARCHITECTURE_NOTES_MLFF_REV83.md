---
title: "MLFF Architecture Revision 83"
subtitle: "CUEQ-REPEAT1-DIAG TRAIN2 FP32 repeatability diagnostic hotfix"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 83

**Release:** `mdstats 0.20.216a0`  
**Dependency-graph schema:** 65  
**Gate:** `CUEQ-REPEAT1-DIAG`

Revision 83 adds a non-authorizing repeatability diagnostic after MPA-0/default TRAIN2 pure-CuEq parity showed run-to-run force-tail fluctuation (`Fmax` observed around `1.059e-5`, `1.371e-5`, and `2.897e-5`, with a later run below `1e-5`) while energy/stress/descriptor maxima remained around `1e-7` and selection stayed identical.

For FP32 phase-separated CuEq TRAIN2 doctor runs, mdstats now executes 10 repeated e3nn evaluations and 10 repeated pure-CuEq evaluations on the exact same deterministic corpus/checkpoint/head. It prints each paired run's `Emax`, `Fmax`, `Frmse`, force p99, force p99.9, count of force components above `1e-5`, `Smax`, `Dmax`, and selection identity. It also prints min/median/p90/max summaries for e3nn-self and CuEq-self force repeatability and the paired cross-backend force statistics, together with PyTorch/CUDA determinism settings.

The diagnostic is persisted as `mdstats.training-acceleration-repeatability-diagnostic.v1` and is explicitly non-authorizing. The revision-82 TRAIN2 policy remains unchanged at FP32 `rtol=1e-5, atol=1e-5`; source/DATA6 and FP64 policies are unchanged. A diagnostic execution problem is a warning, not an implicit policy change.

The revision-82 FINAL-GPU1 v3/HF2 bundle is archival while this measurement is open. The next action is to run MPA-0 `doctor` once under 0.20.216a0 and report the printed repeatability statistics before changing any parity criterion.
