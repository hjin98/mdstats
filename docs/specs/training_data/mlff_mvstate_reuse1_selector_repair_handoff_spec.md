# MVSTATE-REUSE1 selector-to-repair state handoff specification

## Status

Implemented in mdstats 0.20.236a0 / MLFF architecture revision 103. The gate closes the exact-equivalence CPU optimization program and hands the release to `FINAL-GPU1` for the already-deferred accelerator qualification matrix.

## Purpose

Remove duplicated exact sparse-state reconstruction between MVSEL1 and REPAIR1 without changing selector rank authority, target sizes, repair objective/tie semantics, accepted/rejected swaps, terminal order, or MVQUAL authority.

## Implemented realization

MVSEL1 can emit an authenticated reconstructible `TargetMultiViewSelectionStateCache`. The cache contains exact mutable selector-state checkpoints at each materializable target rung: availability, per-family covered/multiplicity/coverage/representative arrays and coverage mass, domain-total gain arrays, hard-obligation state, correlation-unit counts, and the exact accumulated representative utility. Cache identity binds the TARGET-DATA2B reference, MVIDX authority, MVSEL authority/master-order lineage, selector policy, and sparse-kernel schema. Worker count, executor topology, storage location, and persistence layout remain execution state.

REPAIR1 validates the cache before use. On a valid checkpoint, REPAIR starts directly from the exact state at that rung rather than replaying the already-computed MVSEL prefix. The historical replay path remains the exact fallback/oracle for missing, stale, corrupt, or incompatible cache state.

### Exactness boundary after repair divergence

An apparently attractive shortcut was explicitly rejected. After an accepted repair swap, reconstructing a later state from a pure MVSEL checkpoint plus only the selected-set differences changes thousands of FP64 representative-gain entries by roughly `1e-17`--`1e-16` (observed maximum about `8.24e-17`) because the arithmetic history differs. MVSTATE-REUSE1 therefore permits checkpoint jumps **only while repair has not diverged from MVSEL**. After the first accepted swap, REPAIR carries the historical mutable state forward exactly.

For predetermined post-divergence additions, CSR gather preparation may be batched in bounded candidate blocks. This batching changes only sparse-index lookup preparation: every candidate-major FP64 `np.add.at`, clamp, multiplicity, obligation, unit-count, and representative-utility mutation remains in the historical order. Exact state-array qualification is required.

### Persistence and campaign handoff

The state cache is stored as one uncompressed authenticated NPZ bundle plus a canonical manifest. The bundle SHA-256 and per-array scientific array references are checked on restore. This avoids the per-array fsync overhead of an exploratory one-file-per-array realization. On a fresh prepare, campaign code passes the just-built in-memory state cache directly from MVSEL to REPAIR while also persisting it for restart; it does not immediately read back the file it just wrote.

REPAIR-PAR1 may keep one proposal queue alive across repair iterations. Completion order remains non-authoritative and winner reduction remains canonical.

## Qualification and measured result

The common 8,192-candidate/six-family closure fixture preserves the exact FEAS1, NEIGHBOR1, MVIDX1, MVSEL1, REPAIR1, and MVQUAL1 digests. The frozen repair digest is `ab7dc752555114bcd756913187e1d0eb7069c2e9a093f2a8a41130f485cdc33f`; the MVSTATE cache digest is `9904a0c96c83f4fdfe47558dc115d59664ab1a5a5456e687b9d7d3c75c1912db`.

Same-host paired medians against untouched 0.20.235a0 are approximately:

- target chain excluding persistence: `11.998 s -> 11.017 s` (~1.09x);
- REPAIR: `5.365 s -> 4.272 s` (~1.26x);
- one-time state-cache write/read: about `0.176 / 0.125 s` for ~7.0 MiB;
- fresh target chain including the cache write: about `11.193 s` (~1.07x faster than 0.20.235a0);
- cumulative fresh-chain speedup versus PERFBASE1-era 0.20.225a0: about `2.44x`.

Peak RSS rises by about 5.6% on the paired fixture because exact rung state is deliberately retained, remaining far below the campaign memory ceiling.

The complete selector-state arrays are compared against exact replay at cached rungs. Native-store tampering and stale selection lineage are rejected. Cache miss or invalidation falls back to exact selector replay. Cache-backed and replay-oracle REPAIR plans are byte/dictionary identical, including all swaps and terminal order; MVQUAL remains unchanged.

## Closure decision

MVSTATE-REUSE1 is successful. Integrated reprofiling shows that the remaining MVSEL/REPAIR tail is dominated by the exact sequential sparse-state arithmetic itself rather than another material duplicated reconstructible CPU artifact. Further CPU-only decomposition would either target small constant factors or risk changing arithmetic history without a compelling campaign-level payoff.

Therefore the exact-equivalence CPU optimization program is **closed** at revision 103. The next release gate is `FINAL-GPU1`; no positive GPU/CuEquivariance performance claim is made by MVSTATE-REUSE1.
