# MLFF architecture revision 100 - AUDIT-EVAL-PERF1

Release: mdstats 0.20.233a0  
Date: 2026-08-17

Revision 100 closes the Foundation Audit / EVAL2 CPU-hardening gate without changing model inference or scientific authority.

## Implemented

- EVAL2 repeated checkpoint reductions now reuse bounded execution-only static metadata for composition, species, focus groups, and correlation-block coding.
- Force-vector tails use exact preallocation rather than ragged list accumulation plus concatenation.
- Paired block bootstrap preserves the existing deterministic RNG stream while processing draws in memory-bounded vector batches.
- FOUNDATION-AUDIT1 shares one DATA3 frame index and per-run species-membership metadata across domains, reuses squared-error work, and batches configured tail quantiles.
- No extra DATA6/MACE prediction call is introduced.

## Qualification result

Exact control/current metric, bootstrap, and foundation-audit digests are preserved on the frozen CPU fixtures. Repeated EVAL2 target reduction improves by about 1.92x, paired bootstrap by about 3.36x, and the available small Foundation Audit fixture by about 1.06x. The latter is intentionally reported as a modest CPU reduction rather than overstated because prediction-sidecar authentication and structural conditioning remain necessary work.

The active qualification foundation is MACE-MPA-0 medium. The reducer contracts are model-family independent and remain valid for MACE-MH-1.

Next gate: REPLAY-PERF1.
