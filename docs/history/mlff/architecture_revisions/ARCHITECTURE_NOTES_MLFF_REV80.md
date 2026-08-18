---
title: "MLFF Architecture Revision 80"
subtitle: "REPLAY-UNIFY1D single-source campaign integration"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 80

Revision 80 implements **REPLAY-UNIFY1D** and makes the single selected replay corpus the campaign-facing replay authority. New `mdstats mlff campaign init` configurations expose only `[paths].replay_set`; the historical `replay_train`, `replay_monitor`, and `replay_true_labels` options remain hidden compatibility inputs for old automation and may not be mixed with `replay_set`.

The migration uses an explicit adapter boundary. Gate-A/B/C authorities reconstruct the source, true-label cache, prediction/qualification records, deterministic split, and required logical views. mdstats then materializes disposable ExtXYZ train/monitor transport files below `.mdstats/replay-unified/views` and describes those files with the historical `ReplayFileArtifact` contract consumed by TRAIN2/DATA8. This switches the external interface without simultaneously rewriting established downstream scientific schemas.

For `true_dft`, both replay roles are derived directly from the single source and immutable split. For `foundation_pseudolabel`, `prepare` binds the doctor-frozen foundation model/head/inference/runtime realization, reuses the Gate-C batched prediction and audit caches, qualifies the eligible geometry set, freezes the split, and materializes pseudo-label train/monitor plus the independent true-label monitor from exactly the same geometry membership. Source truth is never overwritten. Missing required monitor truth fails closed.

`doctor` validates `replay_set`, source truth, and runtime prerequisites but deliberately does not execute the full replay foundation-model prediction pass. That expensive work first occurs in `prepare`, where the resulting replay authorities are persisted. Prepare/restart receipts now include the single-source config, replay source, true-label cache, foundation prediction policy/cache and pseudo-label qualification when applicable, split manifest, and materialized-view receipts.

Gate D also adds two restart optimizations. `mdstats.replay-source-artifact-receipt.v1` authenticates and reuses source inspection across command processes when the replay SHA and locator are unchanged. Each generated train/monitor transport also has a SHA-bound artifact receipt, avoiding repeated 10k/2k scans. Storage accounting now protects `replay_set` as the sole new-style external replay input.

The supplied 12,000-frame LTA replay source was run through the new campaign-facing `true_dft` integration path. It produced exactly **10,000 train / 2,000 monitor**. Cold plan construction, including source inspection, cache/split construction, materialization, and downstream adapter inspection, measured about 27.6 s on the development CPU host with about 336 MB peak RSS. A process-style restart after clearing only the in-memory context returned in about 0.60 s by reusing persisted receipts. These measurements are host-specific integration evidence, not portable performance claims.

Pseudo-label integration is covered by deterministic provider tests. Real MACE/CUDA/CuEq replay inference remains deliberately deferred to the regenerated FINAL-GPU1 bundle after REPLAY-UNIFY1E.

**Release:** `mdstats 0.20.213a0`  
**Dependency-graph schema:** 62  
**Next gate:** `REPLAY-UNIFY1E` - migration hardening, invalidation/performance qualification, and regenerated FINAL-GPU1 handoff.
