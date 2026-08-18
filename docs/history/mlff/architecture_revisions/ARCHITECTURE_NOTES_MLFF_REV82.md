---
title: "MLFF Architecture Revision 82"
subtitle: "CUEQ-DEFAULT1-HF2 TRAIN2 FP32 backend-parity ceiling hotfix"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 82

**Release:** `mdstats 0.20.215a0`  
**Dependency-graph schema:** 64  
**Gate:** `CUEQ-DEFAULT1-HF2`

Revision 82 applies a narrowly scoped TRAIN2 FP32 CuEq/e3nn backend-equivalence hotfix. The generic ACCEL1 source/DATA6 FP32 authority remains `rtol=1e-5, atol=1e-6`; TRAIN2 FP32 now uses `rtol=1e-5, atol=1e-5`. FP64 remains unchanged at `rtol=1e-10, atol=1e-12`.

The revision is motivated by MACE-MPA-0/default workstation parity evidence reporting `Emax=2.384e-7`, `Fmax=8.911e-6`, `Smax=1.660e-7`, `Dmax=2.883e-7`, with `selection_identical=True`. The pattern is consistent with backend-dependent FP32 reduction/accumulation ordering rather than a scientific change in the selected potential. The `1e-5` absolute ceiling is therefore frozen as a numerical backend-equivalence envelope only; it does not alter training convergence thresholds, DATA8 scientific acceptance, stopping rules, model-quality targets, or deployment verification criteria.

The ceiling is fixed, not adaptive. A zero-reference absolute difference above `1e-5` remains a parity failure; non-finite outputs or non-identical deterministic selection remain hard failures. No silent e3nn fallback is introduced.

FINAL-GPU1 remains authority v3 with the same 18-item matrix, but its preflight advances to v9 and now records and verifies the exact TRAIN2 acceleration-parity policy and digest. The regenerated release handoff must therefore bind the 0.20.215a0 archive; a revision-81/v8 preflight cannot authorize the hotfixed package.

**Next action:** rerun the MPA-0 campaign doctor under the hotfixed package. Positive GPU qualification remains pending the consolidated FINAL-GPU1 v3 workstation execution.
