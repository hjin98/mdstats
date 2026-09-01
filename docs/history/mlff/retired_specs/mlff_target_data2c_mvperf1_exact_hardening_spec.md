# TARGET-DATA2C-MVPERF1 exact-equivalence performance hardening specification

**Release:** `mdstats 0.20.204a0`  
**Architecture:** revision 71 / dependency-graph schema 53  
**Status:** implemented execution-only; production TARGET-DATA2C remains revision-64 v4

## Frozen contract

1. `optimized` and `reference` are execution modes only; they are excluded from MVSEL1/REPAIR1 scientific policy digests.
2. Optimized selection and repair must produce byte-identical persisted plan dictionaries and ordered frame identities versus reference execution on exact qualification fixtures.
3. MVIDX1 scientific arrays remain uint32 indices / uint64 offsets and no dense `N x N` persistence is allowed.
4. Inverse sparse updates are grouped only across consecutive complete witness rows. Witness order and canonical candidate-edge order are preserved exactly. The v1 transient batch target is 262,144 edges; a single row may exceed it rather than being semantically split.
5. FP64 scientific gains, the revision-69 tie hierarchy, revision-70 hard-safe active-shell repair, and all hard 0.95 coverage/obligation predicates are unchanged.
6. REPAIR1 zero-unique telemetry and the initial removal shortlist share one exact shell traversal; state-changing swaps force fresh scans.
7. MVSEL1/REPAIR1 run inside stage resource scopes with one Python lane and bounded native/BLAS threads. Approximate neighbors, GPU graph authority, and locked-test tuning are forbidden.
8. Content-addressed native MVIDX1 persistence, mmap restore, and streamed hash semantics inherited from PERF-P3/P5 remain authoritative.

## Qualification

The release benchmark must include (a) a reference-equivalence sparse fixture with identical selection digest and a measured optimized speedup, and (b) an optimized stress fixture that reaches the full 16,384 selection cardinality under bounded RSS. Functional qualification also requires exact internal state equality after each tested optimized/reference selection step and regression-clean TARGET-DATA2A/B/C/D/E plus campaign restart behavior.

The next gate is `TARGET-DATA2C-MVQUAL1`. MVPERF1 cannot migrate DATA8 membership or generated TARGET-DATA2C policy.
