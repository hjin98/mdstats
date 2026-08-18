# mdstats 0.20.228a0 patch notes

- Completed MLFF optimization gate `MVIDX-REUSE1`.
- Parallelized independent cached-MVIDX family and hard-obligation inversion tasks through `DeterministicWorkQueue`.
- Replaced the per-row CSR sorted/unique validation loop with an exact vectorized boundary-aware predicate.
- Preserved byte-identical inverse adjacency and the frozen MVIDX scientific digest across worker schedules.
- Kept NEIGHBOR1 cache reuse, TARGET-DATA2 scientific semantics, MPA-0/MH-1 foundation support, and GPU authority unchanged.
- Advanced the frozen optimization sequence to `COVREF-PAR1`.
