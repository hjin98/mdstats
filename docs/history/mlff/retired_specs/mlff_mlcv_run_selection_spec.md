# MLFF MLCV-SELECT1 run-local full checkpoint selection specification

Status: implemented in mdstats 0.20.135a0; replay-degradation semantics corrected in mdstats 0.20.140a0 (`MLCV-SELECT1`).

## Scope

MLCV-SELECT1 consumes each run's current MLCV-RANK1 top-K shortlist and performs authoritative run-local full-validation checkpoint acceptance. It never pools checkpoints across folds/seeds, never uses an outer CV fold to select an epoch, and does not choose the production model.

## Inputs

Each completed run provides immutable current RANK1 evidence (default top five), the target/replay score weights and target criterion, the retained safety-metric policy, the run-correct complete target selection artifact, complete independent TRUE_DFT replay validation `R_full`, and authenticated candidate/foundation lineage.

For a CV fold, target selection is `V_i_full` with `TARGET_CHECKPOINT_SELECTION` authority. Outer fold `C_i` has only `TARGET_OUTER_CV_EVALUATION` authority and is forbidden. For a final-development run, target selection is held-out `D_full` with `TARGET_FINAL_VALIDATION` authority.

## Matched replay baseline

SELECT1 uses the foundation baseline measured on the exact same complete replay domain:

`R0_full = RMSE(foundation, R_full)`.

For every candidate:

`DeltaR_full = R_full - R0_full`.

Both raw `R_full` and signed `DeltaR_full` are persisted. Negative degradation is valid and beneficial. Baseline model SHA-256 plus replay artifact digest/SHA bind the zero point; an `R_light` baseline cannot substitute for `R0_full`.

## Full acceptance gates

Every retained RANK1 checkpoint is fully evaluated; SELECT1 does not stop after the first survivor. The component-wise gates are

`T_full <= T_max`

and

`DeltaR_full <= DeltaR_max`,

where, unless explicitly overridden,

`DeltaR_max = (w_T / w_R) * T_max`.

For diagnostics only, the equivalent absolute replay ceiling is

`R_full <= R0_full + DeltaR_max`.

Thus with `R0_full = 75.281 meV/A`, `T_max = 30 meV/A`, and 1:1 weights, a candidate replay RMSE up to `105.281 meV/A` can pass the replay-retention gate. A raw replay value above 30 meV/A is not itself a failure.

Configured energy MAE, focus-force RMSE, stress RMSE, and worst-condition force RMSE limits remain hard gates where present. No scalar score can compensate for a failed target, replay-degradation, or retained safety gate.

`target_stop_fraction` and `replay_stop_multiplier` are STOP1 training-control factors only and do not modify SELECT1 acceptance.

## Representative score

Only full-gate survivors receive

`S_full = (w_T*T_full + w_R*DeltaR_full)/(w_T+w_R)`.

Deterministic ties prefer lower score, lower target RMSE, lower replay degradation, lower absolute replay RMSE, better original lightweight rank, earlier epoch, then checkpoint SHA-256.

## Durable result

Each run receives one immutable current run-selection record with either `representative_selected` or explicit `no_representative`. Current candidate evidence binds target RMSE, absolute replay RMSE, `R0_full`, signed replay degradation, degradation budget, diagnostic absolute ceiling, baseline model SHA, exact full-domain lineage, and score.

Historical v1 records keep their original raw-absolute replay meaning and digest. They are never treated as current degradation evidence without recomputation against authenticated matching foundation baselines.

## Gate boundary

MLCV-SELECT1 does not evaluate a fold representative on untouched `C_i`, aggregate CV statistics, compare final-development seeds, export a production/committee model, perform physical NVE verification, or activate locked target test `E`. Those responsibilities remain AGG1, FINAL1, and VERIFY1.
