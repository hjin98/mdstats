---
geometry: margin=0.65in
fontsize: 9pt
---

# TARGET-DATA2C-MVSEL1 deterministic progressive selector

**Release:** `mdstats 0.20.202a0`  
**Architecture revision:** 69  
**Dependency-graph schema:** 51  
**Status:** implemented as diagnostic/pre-migration selector evidence

MVSEL1 consumes the frozen TARGET-DATA2B coverage reference and exact TARGET-DATA2C-MVIDX1 sparse substrate. It constructs one deterministic ordered coreset through a hard ceiling of 16,384 candidates but does **not** replace the revision-64 TARGET-DATA2C v4 production ladder.

## Frozen decision order

1. gain against currently unsatisfied required hard obligations;
2. marginal coverage of the current worst normalized required view;
3. total newly covered FP64 reference mass;
4. least-selected TARGET-DATA2A correlation-unit balance;
5. density-aware representative gain;
6. normalized sparse-neighborhood diversity;
7. stable frame UID.

Phase A ends only when all required obligations pass and all required family coverage masses are at least 0.95. Phase B then fills remaining cardinality with the harmonic witness-multiplicity marginal objective `weight / (1 + selected_multiplicity)`.

## Incremental exactness

Per-family covered masks, witness multiplicities, candidate coverage gains, candidate harmonic gains, hard-obligation counts, and correlation-unit counts are reconstructible caches. MVIDX1 inverse adjacency is used to update only candidates adjacent to witnesses or obligations whose state changed. Full candidate-by-witness rescoring after every selection is forbidden.

The persisted authority contains the ordered frame-UID sequence and exact rung evidence only. For every materializable rung, validation recomputes covered mass and hard-obligation state directly from MVIDX1 and requires nested-prefix monotonicity. Exact replay qualification requires the same selector digest from the same frozen inputs.

## Migration boundary

The campaign record is `target_multi_view_selection` and is included in the prepare receipt. `target_data_ladder` remains the revision-64 v4 production authority. MVSEL1 cannot alter DATA8 membership, target-size learning candidates, generated defaults, or locked-test behavior. Migration remains deferred through REPAIR1, MVPERF1, MVQUAL1, SIZE-HALVE2, SIZE-FIDELITY2, and MVMIGRATE1.

**Next gate:** `TARGET-DATA2C-REPAIR1`.
