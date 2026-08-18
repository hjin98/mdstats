---
geometry: margin=0.65in
fontsize: 9pt
---

# TARGET-DATA2-MVPLAN1 normative roadmap

**Release:** `mdstats 0.20.198a0`  
**Architecture revision:** `65`  
**Dependency-graph schema:** `47`  
**Status:** architecture freeze only; implementation begins at `TARGET-DATA2B-FEAS1`.

## Frozen scope

The planned selector replaces random/semi-random target ordering with direct deterministic multi-view coverage optimization. It does not flatten the empirical distribution and does not relax TARGET-DATA2B's default 0.95 hard coverage threshold, required extents, protected strata, mandatory reservations, DATA5 leakage/correlation rules, or locked-test boundary.

Generated target-size candidates are planned as exactly:

`128, 256, 512, 1024, 2048, 4096, 8192, 16384`.

`16384` is a hard candidate ceiling. Revision-64 dynamic upper rescue remains current executable behavior until `TARGET-DATA2C-MVMIGRATE1`; after migration, generated campaigns may not silently exceed 16384.

## Selection authority

Before subset optimization, `TARGET-DATA2B-FEAS1` computes full-development-pool feasibility. Full-pool failure yields `support_mismatch`. If the full pool is feasible, selection constructs one exact nested order and uses lexicographic priorities: worst normalized required-view deficit; mandatory/protected-stratum deficit; new weighted reference mass; representative/facility gain; normalized diversity; stable frame identity.

Redundancy is leave-one-out unique coverage, not neighbor count. Clustering score is diagnostic only. Repair swaps are restricted to the active shell and must strictly improve the frozen lexicographic objective without reducing any hard requirement or earlier prefix.

## Successive-fidelity authority

The eight dataset sizes are the Stage-B0 population. The `8 -> 4 -> 2 -> 1` rule refers to **candidate count** at `3 -> 10 -> 30` epochs. All eight may receive bounded 3-epoch evidence; hard-coverage-failing candidates cannot survive. At least four hard-coverage-qualified sizes are required before Stage B1. The generated minimum qualifier requirement therefore advances from three to four only when `SIZE-HALVE2`/migration becomes authoritative.

## Ordered implementation gates

1. `TARGET-DATA2B-FEAS1` - full-pool feasibility/support mismatch diagnostics.
2. `TARGET-DATA2C-MVIDX1` - exact multi-view coverage index/witness substrate.
3. `TARGET-DATA2C-MVSEL1` - deterministic robust progressive selector.
4. `TARGET-DATA2C-REPAIR1` - unique-contribution pruning and deficit-directed shell exchange.
5. `TARGET-DATA2C-MVPERF1` - exact-equivalence performance/memory hardening.
6. `TARGET-DATA2C-MVQUAL1` - same-N A/B scientific qualification and independent audit.
7. `SIZE-HALVE2` - fixed eight-rung 3/10/30 `8 -> 4 -> 2 -> 1` integration.
8. `SIZE-FIDELITY2` - empirical survivor-fidelity requalification on the MV/16k population.
9. `TARGET-DATA2C-MVMIGRATE1` - generated-default migration and revision-64 rescue retirement.

No gate may use locked-test evidence to tune selector objectives, radii, repair budgets, or tie rules. e3nn source/DATA6 and CuEq TRAIN2 execution policy is orthogonal and unchanged.
