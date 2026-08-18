# mdstats 0.20.204a0 patch notes

This release implements **TARGET-DATA2C-MVPERF1** (architecture revision 71 / graph schema 53) as exact-equivalence performance hardening of the diagnostic MVIDX1 -> MVSEL1 -> REPAIR1 path.

- Batches inverse sparse gain updates across consecutive witness rows while preserving exact witness/edge order.
- Bounds transient scatter work to 262,144 edges per execution batch (except an indivisible larger row).
- Retains scalar `reference` execution modes and requires byte-identical persisted selector/repair plans.
- Consolidates REPAIR1's initial zero-unique telemetry and removal-shortlist shell scan.
- Applies StageResourceScope to MVSEL1 and REPAIR1 to prevent nested thread oversubscription.
- Keeps MVIDX1 native sparse/mmap/streamed-hash persistence unchanged.
- Records ~2.7x selector speedup on the reference-equivalence benchmark and successful 16,384-selection stress execution.

TARGET-DATA2C v4 remains the production selector. The next gate is TARGET-DATA2C-MVQUAL1.
