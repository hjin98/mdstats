# MLFF Architecture Revision 91

**Gate:** `DOC-ARCH1`  
**Release:** `mdstats 0.20.224a0`  
**Authority:** documentation structure and frozen performance roadmap; no scientific/runtime authority change

Revision 91 replaces the chronological-growth architecture manual with a state-oriented, indexed manual assembled from numbered chapter sources. Historical architecture notes and patch notes are non-normative lineage under `docs/history/mlff/`; the full revision-90 predecessor is retained as a manual snapshot.

The revision freezes the next exact-equivalence campaign performance program: `PERFBASE1 -> PARCORE1 -> NEIGHBOR1 -> MVIDX-REUSE1 -> COVREF-PAR1 -> MVKERNEL1 -> REPAIR-PAR1 -> MVQUAL-PAR1 -> AUDIT-EVAL-PERF1 -> REPLAY-PERF1 -> CAMPAIGN-PERF-QUAL1`. FEAS1 and MVIDX1 are defined as consumers of one exact-neighborhood substrate so MVIDX1 reuses FEAS1 CSR evidence rather than repeating the geometric search.

Documentation ownership is now explicit: current architecture in `docs/arch_manuals/`, module/contract specifications in `docs/specs/`, user runbooks in `docs/guides/`, historical lineage in `docs/history/`, and qualification/readiness evidence in `release/` and `benchmarks/evidence/`.

## Documentation qualification

The assembled current-state manual is 3,055 lines versus 12,044 lines for the retained revision-90 snapshot. The PDF renders to 45 pages with no overfull TeX boxes. DOC-ARCH1 structure/assembly tests pass 7/7 and the unchanged TARGET-DATA2 runtime path passes 111/111 functional tests.
