# MLFF architecture revision 72 - TARGET-DATA2C-MVQUAL1

**Release:** `mdstats 0.20.205a0`  
**Dependency graph:** schema 54

Revision 72 implements TARGET-DATA2C-MVQUAL1 as the independent same-cardinality scientific qualification authority for the frozen MVIDX1 -> MVSEL1 -> REPAIR1 path.

For every cardinality materializable by both the current TARGET-DATA2C v4 selector and the repaired MV selector, both memberships are rescored directly through immutable TARGET-DATA2B. Selector-internal coverage scores cannot satisfy the gate. DATA2A/MVIDX1 required obligations, including correlation-interval reservations, are checked separately and are part of hard non-regression.

The gate records per-required-family coverage/extent state, protected-stratum state, `D_max`, `D_sum`, common-size `N95`, uncovered witness count/mass, unique-reference-mass fraction, zero-unique-candidate fraction, correlation-unit balance, and run/condition diversity. MVIDX1 telemetry is accepted only after its covered mass agrees with the independent TARGET-DATA2B scorer within the frozen numerical tolerance.

Qualification requires: no legacy hard pass may become an MV fail at the same N; MV `D_max(N)` may not exceed legacy `D_max(N)`; and common-size `N95` may not increase. `D_sum` and redundancy/provenance metrics are secondary diagnostics. All materializable MV rungs, including a 16,384 rung when present, are independently rescored for bounded-capacity diagnosis rather than trusting selector-internal qualification flags.

The smallest one or two common sizes that are independently hard-qualified for both selectors are frozen as legacy-vs-MV learning controls. Positive TRAIN2/EVAL2 execution remains `deferred_final_gpu_qualification`, preserving the project-wide consolidated final-GPU policy.

No DATA8 membership, TARGET-DATA2D survivor policy, TRAIN2 backend, CuEq policy, or generated TARGET-DATA2C default changes. Revision-64 TARGET-DATA2C v4 remains the production selector until MVMIGRATE1.

**Next gate:** SIZE-HALVE2.
