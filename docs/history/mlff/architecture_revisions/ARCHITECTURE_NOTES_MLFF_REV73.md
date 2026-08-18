---
title: "MLFF Architecture Revision 73"
subtitle: "SIZE-HALVE2 fixed-eight qualified-only 3/10/30 funnel"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 73

Revision 73 implements `SIZE-HALVE2` as a separate pre-migration authority. It freezes exactly eight possible target sizes from 128 through 16,384, admits only independently hard-qualified MV sizes to training, requires at least four qualifiers, and implements the exact `q -> min(q,4) -> 2 -> 1` 3/10/30 evidence transitions.

The authority inherits PERF-P2R exact continuation: epoch-10 evidence authenticates epoch-3 checkpoint/optimizer/RNG state, epoch-30 evidence authenticates epoch-10 state, and all candidates share foundation, evaluation-role, TRAIN2-policy, training-run, and schedule identity, exact normalized schedule progress, and increasing exposure. Largest-boundary tie protection remains limited to early practical-equivalence bands; final selection prefers the smaller equivalent size and reports `nonconverged_at_fixed_ceiling` when the largest qualified boundary remains materially superior.

Campaign preparation persists `size_halve2_plan` after MVQUAL1 and includes it in restart receipts. This gate is intentionally pre-migration: revision-64 TARGET-DATA2C v4, TARGET-DATA2D v2, DATA8 membership, and CuEq policy remain unchanged.

**Release:** `mdstats 0.20.206a0`  
**Dependency-graph schema:** 55  
**Next gate:** `SIZE-FIDELITY2`.
