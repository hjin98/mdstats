# MLFF architecture revision 64 - TARGET-DATA2C bounded upper-ladder coverage rescue

**Release:** `mdstats 0.20.197a0`  
**Gate:** `TARGET-DATA2C-RESCUE1`  
**Dependency-graph schema:** `46`

Revision 64 corrects a fixed-ceiling assumption in the production target-size convergence funnel. The base TARGET-DATA2C ladder remains `(128, 256, 512, 1024, 2048, 4096, 8192)`, but `8192` is no longer treated as a universal maximum when the complete TARGET-DATA2B production coverage authority (including DATA6 foundation-residual and profile/environment families) cannot provide the minimum number of hard-coverage qualifiers.

TARGET-DATA2C v4 evaluates the base ladder first. Only when fewer than TARGET-DATA2D `min_coverage_qualifiers` pass does it activate an upper-ladder rescue. Rescue sizes are deterministic aligned prefixes at `3/8`, `4/8`, `5/8`, `6/8`, and `7/8` of the smallest common development-domain pool, omitting values not strictly above the base ceiling. The maximum 7/8 prefix preserves at least a 1/8 common development complement for leakage-safe EVAL2.

The correction does not weaken the hard-coverage authority: default 0.95 reference-mass coverage, extent support, required strata, mandatory reservations, exact nested ordering, and selection determinism are unchanged. All materializable rescue rungs are retained for Stage B0 rather than being truncated by coverage rank. Rescue state, candidate sizes, and the required qualifier count are content-addressed in `TargetDataLadderPlan.v4`; pre-v4 stored ladders rebuild fail-closed.

If even the bounded rescue remains insufficient, TARGET-DATA2D now emits largest-rung family/extent/stratum/mandatory diagnostics so the next decision is evidence-driven rather than an opaque `n8192:FAIL` summary. Source/DATA6 remains e3nn and TRAIN2 remains pure-CuEq by generated policy.
