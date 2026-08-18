# mdstats 0.20.197a0 - TARGET-DATA2C bounded upper-ladder rescue

## Corrected

A production LTA `prepare` run reached TARGET-DATA2D with every fixed target-size rung from n128 through n8192 failing hard coverage. The original fixed ceiling had been performance-tested before the complete production DATA6 model-derived coverage families were available, so `n8192` was incorrectly treated as a universal upper bound for coverage qualification.

TARGET-DATA2C v4 keeps the existing power-of-two base ladder unchanged. When the base ladder yields fewer than `min_coverage_qualifiers`, it activates a deterministic upper-ladder rescue at 3/8, 4/8, 5/8, 6/8, and 7/8 of the smallest authorized development pool, rounded down to the smallest base-rung alignment. Candidates at or below the base ceiling are omitted.

The rescue never consumes the complete development pool. Its maximum is 7/8 of that pool, reserving at least 1/8 for a leakage-safe EVAL2 complement. Every materializable rescue rung remains an exact prefix of the same quota-first, exact-FPS ordering and every hard-coverage-qualified rung proceeds to the epoch-3 learning screen.

## Scientific policy

The coverage threshold, extent checks, required strata, and mandatory-reservation predicates are **not relaxed**. The default `coverage_threshold = 0.95` remains unchanged. This release corrects the candidate-size ceiling, not the scientific admissibility criterion.

The e3nn source/DATA6/evaluation path and CuEq TRAIN2 default are unchanged.

## Restart behavior

Stored pre-v4 TARGET-DATA2C authorities are stale by design and rebuild from the already frozen TARGET-DATA2A/TARGET-DATA2B inputs. The rescue minimum-qualifier requirement is serialized, so changing `min_coverage_qualifiers` invalidates and rebuilds the ladder instead of reusing incompatible state.

## Diagnostics

If the bounded rescue still cannot produce enough qualifiers, TARGET-DATA2D now reports whether rescue was active, the rescue candidate sizes, and the largest-rung family mass/threshold, extent, stratum, and mandatory-obligation failures.
