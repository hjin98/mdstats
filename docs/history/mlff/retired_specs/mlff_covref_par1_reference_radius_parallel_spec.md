# MLFF COVREF-PAR1 exact reference-radius parallelization specification

**Release:** `mdstats 0.20.229a0`  
**Architecture revision:** 96  
**Authority class:** performance exact equivalence

## Scope

COVREF-PAR1 changes TARGET-DATA2B reference construction execution only. It SHALL NOT change the target development domain, correlation-unit weights, robust scaling, extent statistics, reference-mass beta, leave-one-out rule, cKDTree metric, family inclusion, local-radius arrays, or serialized TARGET-DATA2B authority.

## Parallel realization

1. Campaign construction resolves an outer worker count from the configured CPU budget.
2. A single `StageResourceScope` owns the stage with `python_workers=P`, `tree_workers=1`, and `blas_threads=1`.
3. Each family constructs its scaled matrix and read-only cKDTree once.
4. Independent row blocks are submitted through the shared `DeterministicWorkQueue`; every cKDTree query uses `workers=1`.
5. Blocks write to disjoint canonical output slices. Completion order is execution-only.
6. The configured radius block size is an upper bound. The parallel path may reduce it using execution-only cache-working-set and occupancy heuristics.
7. Direct API calls without an execution scope retain the historical native-tree `query_workers` path for compatibility and exact-oracle comparison.

## Adapter hardening

- Pair geometry lookup SHALL be O(1) by frame/rule after one index build.
- Foundation species residual lookup SHALL be O(1) by frame/atomic number after one index build.
- Target-label scalar constant-family rejection SHALL use the exact historical `np.allclose` predicate before robust statistics/tree construction.
- Weight-profile caching and scaled arrays remain reconstructible execution state.

## Acceptance

- PERFBASE1 supplied-family radius digest is exactly `823a2c0c2f8a012c84bee0fe27085535862b71ff48a75f31b6d96e52cd642e2d` for all qualified worker schedules.
- Full TARGET-DATA2B references are dictionary/digest identical between serial historical execution and COVREF-PAR1 execution.
- Parallel work observes all assigned lanes on compute-bound fixtures.
- Nested native-tree parallelism is rejected when an outer execution scope is active.
- The active qualification checkpoint is MACE-MPA-0 medium; the contract is foundation-generic and applies unchanged to MACE-MH-1.
