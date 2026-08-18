# MLFF MLCV-AGG1 conventional cross-validation specification

Status: implemented in mdstats 0.20.136a0 (`MLCV-AGG1`)

## Purpose

MLCV-AGG1 converts frozen per-run MLCV-SELECT1 fold representatives into conventional cross-validation evidence. The outer CV fold is evaluation-only evidence. It cannot stop training, rank epochs, choose among the top-K shortlist, or replace a representative after seeing its result.

## Fold evaluation contract

For fold `i`, SELECT1 first freezes one representative using only the nested checkpoint-selection domains `V_i_light -> V_i_full` plus independent TRUE_DFT replay validation. Only then does AGG1 expose the complete outer target fold `C_i`.

AGG1 evaluates exactly the frozen representative checkpoint on `C_i`. If SELECT1 produced no representative, the fold records an explicit `no_representative` failure and no outer-fold model inference is purchased. If the representative exists, an outer target force-component RMSE is computed and compared with the configured authoritative target ceiling.

An outer result may therefore produce only:

- `passed`;
- `no_representative`; or
- `outer_target_threshold_exceeded`.

It cannot trigger fallback to another epoch or checkpoint from the same fold run.

## Replay semantics

Replay is not a rotating CV domain. AGG1 does not re-infer replay and does not create fold-specific replay partitions. It reuses the frozen representative's authenticated complete TRUE_DFT `R_full` absolute replay RMSE, matched foundation `R0_full`, and signed replay degradation `DeltaR_full = R_full - R0_full` from MLCV-SELECT1.

The deployment-oriented combined fold score is

`S_i = (w_T T_outer,i + w_R DeltaR_full,i) / (w_T + w_R)`.

This combined score is useful operational evidence but does not change the interpretation of `T_outer,i` as the statistically clean rotating target CV quantity.

## Per-seed aggregation

For every configured seed, all configured folds must be represented exactly once. All-fold survival is a hard robustness requirement: every fold must have a SELECT1 representative and every outer target RMSE must satisfy the configured target ceiling.

For target, replay degradation, absolute replay RMSE, and combined score separately, AGG1 reports:

- mean;
- sample standard deviation;
- minimum;
- maximum;
- range; and
- worst fold.

The sample standard deviation uses the conventional `N-1` denominator when at least two folds are available. Cross-fold dispersion is diagnostic-only in AGG1 v1. No hard standard-deviation or range cutoff is introduced without empirical calibration and a future identity-bearing policy revision.

## Production authority

Fold representatives are permanently production-ineligible. AGG1 creates no production model selection and no committee. It publishes CV robustness evidence only. Production comparison across optimizer seeds belongs to MLCV-FINAL1 and may consume only final-development representatives.

## Zero-fold campaigns

A user may intentionally configure zero CV folds. Such a variant is recorded as `cv_not_performed`, not as conventional robustness evidence. It does not manufacture fold statistics.

## Restart and immutability

Outer-fold evaluation records are bound to the campaign run identity, SELECT1 record digest, representative checkpoint SHA/epoch, outer artifact digest/SHA, and AGG1 policy digest. Re-running evaluation may reuse authenticated prediction/evaluation records, but any attempt to bind different outer evidence or a different checkpoint to the same immutable fold record fails closed.


## 0.20.140a0 replay-degradation correction

AGG1 combined scores use the representative's authenticated signed `DeltaR_full`, never raw absolute `R_full`. Absolute replay RMSE remains a separately reported physical diagnostic. Historical aggregate schemas keep their original raw-replay meaning and are stale for current FINAL1 authority.
