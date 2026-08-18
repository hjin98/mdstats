# MLFF architecture revision 103 - MVSTATE-REUSE1

Release: mdstats 0.20.236a0  
Date: 2026-08-17

MVSTATE-REUSE1 closes the exact-equivalence CPU optimization program by handing authenticated exact MVSEL sparse-state checkpoints into REPAIR. REPAIR may jump to a pure selector checkpoint only while no repair swap has been accepted; after divergence it carries the historical mutable state forward. A proposed pure-checkpoint reconciliation after divergence was rejected because it changed FP64 representative-gain entries by roughly 1e-17--1e-16 despite identical selected IDs.

The cache is reconstructible execution state, persisted as one authenticated uncompressed NPZ bundle plus canonical manifest. Fresh campaign execution passes the in-memory cache directly from MVSEL to REPAIR and persists it for restart. Missing, stale, corrupt, or incompatible state falls back to exact selector replay. Bounded CSR gather preparation may be batched only while candidate-major FP64 mutations remain in historical order.

On the common 8,192-candidate/six-family fixture, untouched 0.20.235a0 takes about 12.00 s and MVSTATE-REUSE1 about 11.19 s including the one-time cache write. REPAIR improves about 5.37 s to 4.27 s, with exact FEAS/MVIDX/MVSEL/REPAIR/MVQUAL digests. Cumulative fresh-chain speedup versus PERFBASE1-era 0.20.225a0 is about 2.44x. Remaining target-chain time is dominated by exact sequential sparse-state arithmetic rather than duplicated reconstructible work.

The CPU optimization program is therefore closed. Next gate: FINAL-GPU1 workstation qualification. Positive accelerator evidence remains deferred.
