# mdstats 0.20.136a0 patch notes

## MLCV-AGG1

This release implements the sixth conventional-CV correction gate. After MLCV-SELECT1 freezes one representative per fold run, AGG1 evaluates that exact checkpoint once on the complete untouched outer CV fold. The outer result has no checkpoint-selection authority and can never trigger fallback to another epoch from the same fold.

For each seed, all configured folds must have a SELECT1 representative and every representative must satisfy the configured target force-RMSE ceiling on its untouched outer fold. Failure of either condition marks that seed's CV result not robust. Cross-fold target, representative replay, and deployment-oriented combined score statistics are reported separately as mean, sample standard deviation, minimum, maximum, range, and worst fold. Dispersion is diagnostic-only in v1; no uncalibrated hard SD threshold is introduced.

Replay is not rotated or re-inferred by AGG1. Each fold report reuses the representative's authenticated complete TRUE_DFT `R_full` replay error from SELECT1 and combines it with the new outer-fold target error only for reporting. Fold representatives are explicitly marked production-ineligible. Production comparison remains deferred to MLCV-FINAL1 and is restricted to final-development representatives.
