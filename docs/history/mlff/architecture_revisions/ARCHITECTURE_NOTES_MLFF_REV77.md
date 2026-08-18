---
title: "MLFF Architecture Revision 77"
subtitle: "REPLAY-UNIFY1 freeze and single-source replay authority"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 77

Revision 77 freezes REPLAY-UNIFY1 before the actual FINAL-GPU1 workstation execution and implements Gate A. New campaigns will ultimately expose one `[paths].replay_set` selected corpus plus `[replay].label_mode`; the default train:monitor policy is `5:1` with seed `42`. mdstats owns qualification, partition membership, true/pseudo label views, provenance, caching, and reconstruction. Legacy split-file replay campaigns remain readable during migration, and mixed new/legacy path authority is rejected.

The architecture separates source indexing, label caches, qualification, split membership, and materialized MACE ExtXYZ views into independently fingerprinted layers. This ensures ratio/seed changes do not rerun foundation inference, threshold changes reclassify cached prediction/audit evidence, and deleted materializations are reconstructed without inference. Foundation-model/head/runtime changes invalidate pseudo predictions; source geometry changes invalidate all downstream replay authority.

Gate A introduces `mdstats.replay-geometry-identity.v1`, using atom-order-preserving atomic numbers plus Cartesian positions/cell quantized to `1e-8 Angstrom` and explicit PBC. This new identity is not applied retroactively to historical ReplayFileArtifact v3/v4 records. `ReplaySourceArtifact` records one streamed selected replay corpus, source-label inventory, geometry-set identity, and source ordering. `ReplaySplitManifest` binds source geometry-set/qualification identity and exact train/monitor geometry membership. Seeded SHA-256 ranking makes membership independent of ExtXYZ order. An unfiltered 12,000-frame source therefore maps exactly to 10,000 train and 2,000 monitor frames under the default 5:1 policy.

Source true labels and foundation pseudo-labels are frozen as separate logical namespaces; neither may overwrite the other internally. `REF_*` names become materialization-only transport fields in later gates. Production pseudo-label execution will use existing batched/cached MACE infrastructure rather than the historical one-frame-at-a-time standalone preparation loop.

The remaining gates are: REPLAY-UNIFY1B true-label cache/materialization; REPLAY-UNIFY1C batched pseudo-label cache/qualification; REPLAY-UNIFY1D campaign/DATA8/TRAIN2 interface migration; and REPLAY-UNIFY1E hardening, invalidation/performance qualification, documentation, and final FINAL-GPU1 bundle regeneration.

Because REPLAY-UNIFY1 changes the release-matched replay interface before positive GPU execution, the revision-76 FINAL-GPU1 workstation bundle is now archival rather than the final qualification handoff. The FINAL-GPU1 v2 qualification engine remains implemented, but a fresh one-shot workstation bundle will be generated only after REPLAY-UNIFY1E.

**Release:** `mdstats 0.20.210a0`  
**Dependency-graph schema:** 59  
**Next gate:** `REPLAY-UNIFY1B` - true-label cache and lazy materialization from the single replay source.
