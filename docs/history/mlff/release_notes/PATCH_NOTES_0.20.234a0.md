# mdstats 0.20.234a0 - REPLAY-PERF1

- Add authenticated `ReplaySourceIndex` byte-offset/natoms caching for the immutable single replay source.
- Rebuild the index on source mutation or corrupt/stale cache receipts; allow identical-byte relocation without scientific change.
- Route true-label, pseudo-label, and replay foundation-prediction source iteration through deterministic indexed frame access.
- Direct sparse role reconstruction to only the source frames required by that role.
- Reuse authenticated source-order geometry identities rather than recomputing geometry hashes after every parse.
- Keep ASE ExtXYZ parsing serial because direct parser-thread benchmarking was slower.
- Preserve exact REPLAY-UNIFY1 source/split/label/prediction/view authority.
- Active qualification: MACE-MPA-0 medium; implementation remains MACE-MH-1 compatible.
- Next gate: CAMPAIGN-PERF-QUAL1.
