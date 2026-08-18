---
geometry: margin=0.58in
fontsize: 9pt
---

# MLFF Architecture Revision 68 - TARGET-DATA2C-MVIDX1

**Release:** `mdstats 0.20.201a0`  
**Date:** 2026-08-16  
**Dependency-graph schema:** `50`

Revision 68 implements the second gate of the optimized multi-view target-selection roadmap: **TARGET-DATA2C-MVIDX1**.

The gate converts the frozen TARGET-DATA2B required-family coverage geometry into exact bidirectional sparse scientific evidence. Every required family persists witness-to-candidate and candidate-to-witness adjacency with `uint32` indices and `uint64` offsets. Hard lower/upper extent obligations, TARGET-DATA2B strata, and every TARGET-DATA2A development correlation interval are indexed separately in both directions, with explicit candidate correlation-unit codes.

Scientific graph arrays are persisted as authenticated content-addressed NPY sidecars. The manifest binds upstream TARGET-DATA2B, TARGET-DATA2A and FEAS1 identities plus family/domain/obligation metadata and array SHA-256 identities. Future MVSEL1 heaps, gain vectors, masks, and scratch arrays remain reconstructible caches outside scientific authority.

MVIDX1 is integrated into `prepare` as `target_coverage_sparse_index` after FEAS1 and before TARGET-DATA2C. This release does **not** change target selection: revision-64 TARGET-DATA2C v4 and its rescue remain executable until the later selector/repair/performance/qualification/fidelity gates close and MVMIGRATE1 explicitly migrates policy.

**Next gate:** `TARGET-DATA2C-MVSEL1`, the deterministic two-phase progressive selector using this exact sparse substrate.
