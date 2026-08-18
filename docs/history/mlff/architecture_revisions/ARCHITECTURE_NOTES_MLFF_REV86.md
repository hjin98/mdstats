---
title: "MLFF Architecture Revision 86"
subtitle: "CUEQ-REPEAT1-PARITY1 permanent TRAIN2 FP32 noise-normalized parity"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.8in
fontsize: 10pt
---

# Revision 86

**Release:** `mdstats 0.20.219a0`  
**Dependency-graph schema:** 68  
**Gate:** `CUEQ-REPEAT1-PARITY1`

Revision 86 freezes the permanent TRAIN2 FP32 e3nn/pure-CuEq backend-equivalence policy from the MPA-0 DIAG3 workstation evidence. The old one-shot force `allclose` ceiling is retired because same-backend FP32 force variability is comparable to, and sometimes larger than, e3nn/CuEq variability.

The authorizing ordinary production-path probe discards one warm-up evaluation per backend, retains ten post-warm-up outputs per backend, and computes 45 e3nn-self, 45 CuEq-self, and 100 e3nn/CuEq all-pairs comparisons. Selection identity is mandatory across all self and cross pairs.

Stable energy, stress, and descriptor channels return to the tight FP32 `rtol=1e-5`, `atol=1e-6` authority. Force equivalence is normalized against measured same-backend noise. For `Frmse`, `Fp99`, and `Fp99.9`, the p99 cross statistic must not exceed `1.25` times the larger p99 self-backend statistic. `Fmax` is retained only as a catastrophic-tail guard and must remain below both `1.5 x` the observed self-backend `Fmax` envelope and `1e-4 eV/A`.

The MPA-0 DIAG3 ordinary evidence motivating the freeze had p99 ratios approximately `1.08` (`Frmse`), `1.02` (`Fp99`), and `0.90` (`Fp99.9`), with cross `Fmax=2.261e-5` versus a same-backend envelope of `2.337e-5`; selection was identical in `100/100` cross comparisons. The isolated deterministic-control evidence additionally showed post-warm-up e3nn self pairs were exactly zero while CuEq retained stochastic FP32 force variability, confirming the force tail is an execution-noise property rather than a systematic model disagreement.

The deterministic-control subprocess remains available as an optional diagnostic but is removed from routine authorization. FINAL-GPU1 preflight advances to v10 and binds both the stable-channel parity policy and the new noise-normalized force-policy digests.
