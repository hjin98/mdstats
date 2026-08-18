---
title: "MLFF Architecture Revision 85"
subtitle: "CUEQ-REPEAT1-DIAG3 warm-up + all-pairs repeatability refinement"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.8in
fontsize: 10pt
---

# Revision 85

**Release:** `mdstats 0.20.218a0`  
**Dependency-graph schema:** 67  
**Gate:** `CUEQ-REPEAT1-DIAG3`

The revision-84 MPA-0/default workstation evidence confirmed that TRAIN2 FP32 force differences are dominated by a stochastic execution envelope rather than a stable e3nn/pure-CuEq offset. In ordinary execution, e3nn-self `Fmax` reached `1.962e-5`, CuEq-self `1.836e-5`, and cross-backend `2.270e-5`. Under the isolated deterministic controls, e3nn-self comparisons against run 1 became a constant `1.061e-5`, while CuEq-self still reached `2.709e-5` and cross-backend `1.550e-5`. Selection remained identical throughout.

The constant deterministic e3nn self value exposed a second problem with the temporary diagnostic: every self comparison used run 1 as its reference, so a first-call/warm-up shift could contaminate all nine reported self comparisons. Revision 85 removes that arbitrary baseline.

Each backend now receives one complete **discarded warm-up evaluation** on the exact doctor probe. Ten post-warm-up outputs are then retained for e3nn and ten for pure CuEq. No additional model calls are needed for pair construction. mdstats computes offline:

- `C(10,2) = 45` e3nn-self pairs;
- `C(10,2) = 45` CuEq-self pairs;
- `10 x 10 = 100` e3nn/CuEq cross-backend pairs.

Every pair records `Fmax`, force RMSE, force absolute-error p99 and p99.9, the number of force components above `1e-5`, energy/stress/descriptor maximum errors, and selection identity where applicable. Terminal summaries report `min`, `median`, `p90`, `p99`, and `max` instead of printing all 100 cross pairs.

The ordinary diagnostic record advances to `mdstats.training-acceleration-repeatability-diagnostic.v2`. Historical v1 records remain readable and are interpreted using their original baseline-comparison semantics. The isolated deterministic-control subprocess remains schema v1 at the outer wrapper but carries the new v2 repeatability record when completed.

Revision 85 remains **non-authorizing**. TRAIN2 FP32 parity stays at `rtol=1e-5, atol=1e-5`; source/DATA6 and FP64 tolerances are unchanged. FINAL-GPU1 remains archival until the DIAG3 workstation distributions are reviewed and a permanent noise-normalized backend-equivalence criterion is frozen.
