---
geometry: margin=0.65in
fontsize: 10pt
---

# TARGET-DATA2C-RESCUE1 bounded upper-ladder coverage rescue

**Release:** `mdstats 0.20.197a0`  
**Architecture revision:** `64`  
**Authority:** `mdstats.target-data2c.ladder.2026-08.v4`

## Trigger

Build and score the frozen base target-size ladder first. Activate rescue only when the number of globally hard-coverage-qualified base rungs is below TARGET-DATA2D `min_coverage_qualifiers` (default 3).

## Rescue sequence

Let `P` be the smallest authorized TARGET-DATA2A development-pool size across label domains and `A` the smallest base target size. For each numerator `k in {3,4,5,6,7}`, compute `floor((k*P/8)/A)*A`. Retain unique values strictly greater than the largest base rung and strictly less than `P`. Sort them with the base ladder and materialize every globally available candidate as an exact prefix of the same TARGET-DATA2C deterministic ordering.

The `7/8` ceiling guarantees at least a `1/8` common development complement for leakage-safe EVAL2. No full-pool rescue rung is legal.

## Scientific invariants

- Default TARGET-DATA2B hard coverage remains 0.95; no coverage tolerance is relaxed.
- Extent, required-stratum, mandatory-reservation, exact-FPS, and nested-monotonicity predicates are unchanged.
- Coverage is an admissibility gate only. It does not rank or truncate the materializable rescue candidates before Stage B0.
- Rescue activation, rescue sizes, and the minimum qualifier count are serialized and content-addressed.
- A changed minimum qualifier count invalidates stored TARGET-DATA2C authority.
- Pre-v4 TARGET-DATA2C authority is stale for generated campaigns and rebuilds from frozen upstream records.
- Acceleration is unchanged: source inference/DATA6/evaluation remain e3nn and TRAIN2 remains CuEq under CUEQ-DEFAULT1.

## Failure

If fewer than the required qualifiers remain after the bounded rescue, TARGET-DATA2D fails closed and reports rescue state plus largest-rung family mass/threshold, extent failures, failed strata, and unsatisfied mandatory obligations.

