---
title: "MLFF Architecture Revision 75"
subtitle: "TARGET-DATA2C-MVMIGRATE1 atomic generated-policy migration latch"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 75

Revision 75 implements `TARGET-DATA2C-MVMIGRATE1` as the only legal transition from the revision-64 v4 dynamic-rescue path to the exact sparse multi-view fixed-eight generation. The migrated record family is TARGET-DATA2C v5, TARGET-DATA2D v3, and TARGET-DATA2E v3. v5 uses only REPAIR1 master-order prefixes at 128, 256, 512, 1024, 2048, 4096, 8192, and 16384; coverage and mandatory obligations are independently reconstructed rather than trusted from selector-internal scores; four hard qualifiers are required; and dynamic rescue is absent.

The implementation is deliberately two-phase because positive GPU qualification was frozen for final release. CPU/control-plane preparation may build and authenticate the exact v5 candidate and the migration decision lineage, but it cannot activate generated defaults. Activation requires passed MVQUAL1 paired legacy-vs-MV learning controls and a passed SIZE-FIDELITY2 report whose GPU status is exactly `passed`. Missing evidence remains pending; failure blocks migration. This preserves the project rule that GPU qualification occurs once against the complete release package.

Historical v4/v2/v2 records remain readable. v5/v3/v3 schemas are generation-separated so old authorities cannot masquerade as the migrated generation. Restart invalidation is content-addressed at the migration boundary, allowing valid DATA6, TARGET-DATA2A/B, MVIDX1, MVSEL1, and REPAIR1 products to survive final-GPU evidence updates. DATA8 membership, e3nn source/DATA6 policy, CuEq TRAIN2 policy, and the 0.95 independent hard-coverage threshold are unchanged.

**Release:** `mdstats 0.20.208a0`  
**Dependency-graph schema:** 57  
**Next action:** `FINAL-GPU1` consolidated qualification and atomic v5/v3/v3 activation on pass.
