# MVQUAL-PAR1 cloud-CPU qualification benchmark

Release: `0.20.232a0`  
Architecture revision: `99`  
Gate: `MVQUAL-PAR1`  
Active qualification foundation: MACE-MPA-0 medium (`75428afe...638`)  
MACE-MH-1 compatibility: retained

## Authority

This is an exact-equivalence execution gate. The 16,000-reference, six-size, 12-job same-N fixture produces the same complete qualification-plan digest under the untouched 0.20.231a0 production numeric contract and every qualified 0.20.232a0 worker schedule:

`2ebd7f5dc2b560e3150fe4849e7098be2eff56469779f15b2befda74059fc90b`

Campaign execution remains BLAS/OpenMP=1. Unscoped direct API calls retain their historical native-thread environment; worker-count control is not allowed to redefine the scientific record.

## Same-host paired result

| Realization | Warm median |
|---|---:|
| 0.20.231a0 serial same-N; cKDTree workers=4 | 0.866 s |
| 0.20.232a0 global queue; 4 outer lanes; tree worker/job=1 | 0.409 s |

End-to-end speedup: **2.12x**.

## Current scaling

| Outer lanes | Warm median | Max busy |
|---:|---:|---:|
| 1 | 0.828 s | 1 |
| 2 | 0.451 s | 2 |
| 4 | 0.458 s | 4 |

The 1→2 gain is **1.83x**. Four lanes are flat on this cloud CPU because the independent score jobs become memory-bandwidth/allocation limited; automatic campaign mode therefore caps MVQUAL at four outer lanes, while an explicit higher override remains available for a qualified high-bandwidth host.

Queue telemetry on the 4-lane qualification probe observed all four workers active, 12/12 jobs completed, and no queue or memory backpressure.

## Acceptance

PASS. Same-N qualification records, comparison order, hard-obligation state, MVIDX cross-checks and final pass/fail authority are unchanged. `AUDIT-EVAL-PERF1` is next.
