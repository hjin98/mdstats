---
title: "MLFF Architecture Revision 74"
subtitle: "SIZE-FIDELITY2 admission-width survivor requalification"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 74

Revision 74 implements `SIZE-FIDELITY2` as a pre-migration, GPU-deferred scientific control plane over the fixed-eight MV target-size funnel. The authority calibrates every scientifically available admission width `q = 4, 5, 6, 7, 8` from one exhaustive set of uninterrupted 30-epoch trajectories. Calibration disables halving during execution: each frozen optimizer seed trains every hard-qualified size once to epoch 30, and the 3- and 10-epoch survivor decisions are reconstructed retrospectively from those same checkpoints.

The hard fidelity criterion is finalist recall rather than rank correlation. For each seed and admission width, the complete 30-epoch population defines the two eventual target finalists under the frozen practical-equivalence ordering. Both finalists must survive the reconstructed epoch-3 `q -> min(q,4)` stage and the epoch-10 `4 -> 2` stage. A material advantage of the 16,384 boundary beyond the practical-equivalence width fails the bounded-ceiling authority instead of being interpreted as convergence.

SIZE-FIDELITY2 also inherits the prior monitor-efficiency plan. Monitor sizes `128, 256, 512, 1024` are derived from one authorized epoch-3 full prediction product, so monitor calibration adds zero model inference passes. The smallest monitor giving exact epoch-3 promotion-set equivalence across all seeds and available q widths is recommended.

Campaign `prepare` now persists `size_fidelity2_execution_plan` and includes it in restart receipts. The plan is work-authorizing only when SIZE-HALVE2 is ready; otherwise it is a fail-closed no-work record. Positive MACE/GPU calibration remains deferred to `FINAL-GPU1`, so this revision does not claim real accelerator survivor recall and does not change revision-64 TARGET-DATA2C v4, TARGET-DATA2D v2, DATA8 membership, or generated defaults.

**Release:** `mdstats 0.20.207a0`  
**Dependency-graph schema:** 56  
**Next gate:** `TARGET-DATA2C-MVMIGRATE1`.
