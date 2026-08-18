---
title: "MLFF Architecture Revision 81"
subtitle: "REPLAY-UNIFY1E hardening closure and FINAL-GPU1 v3 regeneration"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 81

**Release:** `mdstats 0.20.214a0`  
**Dependency-graph schema:** 63  
**Gate:** `REPLAY-UNIFY1E`

Revision 81 closes the five-gate single-source replay migration. `ReplayInvalidationPlan` makes the frozen invalidation matrix executable and serializable; mutation, duplicate, overlap, tamper, lazy reconstruction, source relocation, and true/pseudo geometry-identity boundaries are qualified. Identical-byte replay relocation reuses the authenticated source receipt without reparsing ExtXYZ.

The supplied 12,000-frame LTA replay authority remains exactly 10,000 train plus 2,000 monitor under the default 5:1 split. Existing CPU/control-plane measurements remain development-host evidence only.

FINAL-GPU1 is regenerated as authority v3. `REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION` is a new must-pass runtime-bound gate, ensuring the integrated batched foundation replay prediction path receives release-matched CUDA/CuEq evidence before final authorization. Historical FINAL-GPU1 v1/v2 records remain deserializable, but the 0.20.209a0 handoff is superseded.

**Next action:** execute the regenerated one-shot FINAL-GPU1 v3 bundle on the final CUDA workstation.
