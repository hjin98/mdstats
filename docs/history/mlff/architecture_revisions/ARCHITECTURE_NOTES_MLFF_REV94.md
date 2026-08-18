# MLFF Architecture Revision 94

**Gate:** `NEIGHBOR1`  
**Release:** `mdstats 0.20.227a0`  
**Authority:** runtime execution optimization under exact scientific equivalence

Revision 94 implements one exact neighborhood engine shared by TARGET-DATA2B FEAS1 and TARGET-DATA2C MVIDX1. FEAS1 now streams its exact witness->candidate relation into canonical CSR while committing the unchanged support/capacity reduction. Ragged cKDTree results are discarded at the canonical reducer boundary; the cache therefore retains compact sparse arrays rather than Python neighborhood objects.

The cache is content-addressed reconstructible execution state. Identity binds the TARGET-DATA2B family/domain ordering and exact metric semantics but excludes worker/block/queue controls. Authenticated native-array persistence supports campaign restart. Final CSR bytes are reserved against the stage RAM budget before RAM materialization.

MVIDX1 now consumes the authenticated forward CSR and skips geometric search on cache hit. If the cache is absent/stale/corrupt, MVIDX1 rebuilds it once through the same global PARCORE1/NEIGHBOR1 engine and persists it. The former duplicate geometry implementation has been removed from the MVIDX module. Its existing CSR-to-CSC inversion is intentionally retained for the next `MVIDX-REUSE1` gate.

On the PERFBASE1 synthetic authority, FEAS1 and MVIDX1 retain their frozen digests and the 3,194,880-edge NEIGHBOR1 store has stable digest `0220c89084fe957e85eb1e1c87a581eaa44869f11cb98bee7f7bd8cdafd3d74e`. Final same-host two-repeat medians show about 2.68x lower three-lane FEAS1->MVIDX1 wall time versus untouched 0.20.226a0.

The active qualification uses the supplied MACE-MPA-0 medium checkpoint. NEIGHBOR1 is foundation-generic and preserves MACE-MH-1 support; no model inference, training, evaluation, or GPU authority changes.

Canonical evidence is recorded under `benchmarks/` and `release/qualification_logs/`. `MVIDX-REUSE1` is next.
