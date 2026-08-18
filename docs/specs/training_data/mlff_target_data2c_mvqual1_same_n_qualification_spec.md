# TARGET-DATA2C-MVQUAL1 - independent same-N qualification

**Release:** `mdstats 0.20.205a0`  
**Architecture:** revision 72  
**Dependency graph:** schema 54

## Authority

MVQUAL1 compares production TARGET-DATA2C v4 with repaired MV membership at identical materializable cardinality. Pass/fail evidence is recomputed through independent TARGET-DATA2B scoring; cached MVSEL1/REPAIR1 coverage cannot satisfy the gate. DATA2A/MVIDX1 hard obligations, including correlation intervals, are checked separately.

For every common N, record required-family coverage/extents, protected strata, hard obligations, `D_max(N)`, `D_sum(N)`, uncovered count/mass, unique-reference-mass fraction, zero-unique-candidate fraction, correlation-unit balance, and run/condition diversity.

## Hard acceptance

A common-N comparison passes only when:

1. every legacy required coverage/extent/stratum/hard-obligation pass remains a pass for MV;
2. `D_max_MV(N) <= D_max_legacy(N) + tolerance`;
3. common independently hard-qualified `N95` does not increase.

`D_sum` and redundancy/provenance telemetry are secondary diagnostics and cannot hide a worst-view regression. Locked-test data cannot tune selector policy. All materializable MV rungs are independently rescored for capacity diagnosis; selector-internal pass flags are not evidence for the 16,384 ceiling.

## Learning controls and migration

Freeze at most two common sizes that hard-qualify independently for both selectors, preferring the smallest and then the next larger control. They become legacy-vs-MV TRAIN2/EVAL2 controls; positive GPU execution is `deferred_final_gpu_qualification`.

The persisted campaign record is `target_multi_view_qualification` and is receipt-bound to TARGET-DATA2B, FEAS1, DATA2A, MVIDX1, the legacy ladder, REPAIR1, and MVQUAL1 policy identity. MVQUAL1 remains pre-migration evidence: revision-64 TARGET-DATA2C v4 is still production authority. Next gate: `SIZE-HALVE2`.
