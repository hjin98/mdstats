# MLFF architecture revision 71 - TARGET-DATA2C-MVPERF1

**Release:** `mdstats 0.20.204a0`  
**Dependency graph:** schema 53

Revision 71 implements exact-equivalence execution hardening for the frozen MVIDX1 -> MVSEL1 -> REPAIR1 path. Consecutive witness rows are applied through bounded witness-order sparse scatters, REPAIR1 consolidates duplicate initial shell scans, and MVSEL1/REPAIR1 execute under explicit stage resource scopes. The scalar reference execution modes remain available for qualification and produce byte-identical persisted plans on the frozen fixtures.

Measured CPU evidence shows approximately 2.7x selector speedup on the denser reference-equivalence benchmark with essentially unchanged RSS, while the optimized cardinality stress case completes all 16,384 selections at 32,768 candidates in about 7.1 s on this host. Lazy heaps and approximate neighbors are not adopted because exact vectorized arbitration is already bounded and deterministic, while sparse updates remain the dominant cost.

No scientific selector policy, hard-coverage criterion, repair objective, DATA8 membership, TRAIN2 behavior, or generated default changes. Revision-64 TARGET-DATA2C v4 remains the production selector until MVMIGRATE1.

**Next gate:** TARGET-DATA2C-MVQUAL1.
